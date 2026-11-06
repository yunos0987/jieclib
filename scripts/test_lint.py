#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/lint.py.

Every rule has at least one violating input (bad*.iec) and one clean input
(good*.iec) under scripts/lint_testdata/<rule>/. The inputs are linted as if
they were under src/, so that the src-only rules apply.

Usage:
  python scripts/test_lint.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import lint  # noqa: E402

_TESTDATA = os.path.join(_HERE, 'lint_testdata')


def _quiet_main(argv, root):
    # Run lint.main without printing its report.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return lint.main(argv, root=root)

# Number of findings of the rule that each violating input must produce.
_EXPECTED = {
    ('keyword-case', 'bad.iec'): 5,
    ('doc-apostrophe', 'bad.iec'): 1,
    ('doc-apostrophe', 'bad_double_quote.iec'): 1,
    ('doc-missing', 'bad.iec'): 2,
    ('doc-style', 'bad.iec'): 3,
    ('doc-language', 'bad.iec'): 3,
    ('no-continue', 'bad.iec'): 1,
    ('no-c-comment', 'bad.iec'): 1,
    ('test-fact', 'bad.iec'): 2,
    ('parse', 'bad_comment.iec'): 1,
    ('parse', 'bad_nested.iec'): 1,
}


def _lint_testdata(rule, name):
    with open(os.path.join(_TESTDATA, rule, name), 'rb') as f:
        text = f.read().decode('utf-8')
    return lint.lint_text(text, 'src/lint_testdata/{}/{}'.format(rule, name))


class RuleTest(unittest.TestCase):

    def test_every_rule_has_bad_and_good_inputs(self):
        for rule in lint.RULES:
            names = os.listdir(os.path.join(_TESTDATA, rule))
            self.assertTrue(any(n.startswith('bad') for n in names), rule)
            self.assertTrue(any(n.startswith('good') for n in names), rule)

    def test_every_bad_input_has_an_expected_count(self):
        for rule in lint.RULES:
            for name in os.listdir(os.path.join(_TESTDATA, rule)):
                if name.startswith('bad'):
                    self.assertIn((rule, name), _EXPECTED)

    def test_bad_inputs(self):
        for (rule, name), count in sorted(_EXPECTED.items()):
            with self.subTest(rule=rule, name=name):
                findings = _lint_testdata(rule, name)
                got = [f for f in findings if f.rule == rule]
                self.assertEqual(count, len(got), [f.format() for f in findings])

    def test_good_inputs(self):
        for rule in lint.RULES:
            for name in sorted(os.listdir(os.path.join(_TESTDATA, rule))):
                if not name.startswith('good'):
                    continue
                with self.subTest(rule=rule, name=name):
                    findings = _lint_testdata(rule, name)
                    self.assertEqual([], [f.format() for f in findings])

    def test_finding_format(self):
        findings = _lint_testdata('no-continue', 'bad.iec')
        self.assertEqual(
            'src/lint_testdata/no-continue/bad.iec:12: error: no-continue: '
            'continue is not supported in the OMRON environment',
            findings[0].format())

    def test_doc_missing_applies_only_to_src(self):
        text = 'function F1: dint\n\tF1 := 1;\nend\n'
        self.assertEqual(['doc-missing'], [f.rule for f in lint.lint_text(text, 'src/a.iec')])
        self.assertEqual([], lint.lint_text(text, 'test/a.iec'))

    def test_macro_names_from_other_files_are_not_keywords(self):
        text = '(*{doc A.}*)\nfunction F1: dint\n\tvar\n\t\tname: STRING;\n\tend\n\tF1 := 1;\nend\n'
        self.assertEqual(['keyword-case'], [f.rule for f in lint.lint_text(text, 'src/a.iec')])
        self.assertEqual([], lint.lint_text(text, 'src/a.iec', frozenset(['STRING'])))

    def test_dollar_escapes_the_closing_brace_of_a_pragma(self):
        # jiepp reads "$}" as an escaped brace, also outside a string
        # ("(*{doc costs 5$} x}*)" gives the documentation "costs 5} x").
        text = '(*{doc costs 5$} x}*)\nfunction F1: dint\n\tF1 := 1;\nend\n'
        scan = lint.Scan(text)
        self.assertEqual([' costs 5$} x'], [d.body for d in scan.docs])
        self.assertEqual([], lint.lint_text(text, 'src/a.iec'))

    def test_member_names_are_not_keywords(self):
        text = '(*{doc A.}*)\nfunction F1: dint\n\tF1 := axis.Max + axis.Time;\nend\n'
        self.assertEqual([], lint.lint_text(text, 'src/a.iec'))

    def test_unterminated_quote(self):
        self.assertFalse(lint._unterminated_quote("doesn$27t, '=' and \"x'y\""))
        self.assertFalse(lint._unterminated_quote("'a$'b'"))
        self.assertTrue(lint._unterminated_quote("doesn't"))
        self.assertTrue(lint._unterminated_quote("$' is not an escape outside a string"))
        self.assertTrue(lint._unterminated_quote("'x' and \"y"))

    def test_language_keys_are_stable_and_unique(self):
        text = '// 日本語\n// 日本語\n// English\n// 別の行\n'
        keys = [f.key for f in lint.lint_text(text, 'test/a.iec')]
        self.assertEqual(['test/a.iec: 日本語', 'test/a.iec: 日本語 #2', 'test/a.iec: 別の行'], keys)
        moved = '\n\n' + text
        self.assertEqual(keys, [f.key for f in lint.lint_text(moved, 'test/a.iec')])


class BaselineTest(unittest.TestCase):

    def test_dump_and_load(self):
        baseline = {'test-fact': {'b', 'a'}, 'doc-language': {'z: 日本'}}
        text = lint.dump_baseline(baseline)
        self.assertEqual(
            '{\n  "doc-language": [\n    "z: 日本"\n  ],\n  "test-fact": [\n    "a",\n    "b"\n  ]\n}\n',
            text)
        self.assertEqual(baseline, lint.load_baseline_text(text, 'x'))

    def test_load_rejects_invalid_input(self):
        for text in ('[', '[]', '{"no-such-rule": []}', '{"test-fact": "a"}',
                     '{"test-fact": [1]}', '{"keyword-case": []}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    lint.load_baseline_text(text, 'x')

    def test_additions(self):
        base = {'test-fact': {'a'}}
        self.assertEqual([], lint.baseline_additions({'test-fact': {'a'}}, base))
        self.assertEqual([], lint.baseline_additions({'test-fact': set()}, base))
        self.assertEqual([('test-fact', 'b')],
                         lint.baseline_additions({'test-fact': {'a', 'b'}}, base))
        # A section that the base does not have is a new rule and may be added.
        self.assertEqual([], lint.baseline_additions(
            {'test-fact': {'a'}, 'doc-language': {'x'}}, base))


_BAD_TEST = 'TEST_S(test_one)\n\tEXPECT_EQ(1, 1);\nEND_TEST_S\n'
_GOOD_TEST = 'TEST_S(test_two)\n\t// Fact: Two.\n\tEXPECT_EQ(2, 2);\nEND_TEST_S\n'


class MainTest(unittest.TestCase):
    """Runs main() on a temporary repository."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'test'))
        os.makedirs(os.path.join(self.root, 'scripts'))
        self.write('test/test_a.iec', _BAD_TEST)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        with open(os.path.join(self.root, rel), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def read_baseline(self):
        with open(os.path.join(self.root, 'scripts', 'lint_baseline.json'), encoding='utf-8') as f:
            return json.load(f)

    def run_main(self, *argv):
        return _quiet_main(list(argv), self.root)

    def test_new_warning_fails_until_it_is_in_the_baseline(self):
        self.assertEqual(1, self.run_main())
        self.assertEqual(0, self.run_main('--reset-baseline'))
        self.assertEqual({'doc-language': [], 'test-fact': ['test/test_a.iec: test_one']},
                         self.read_baseline())
        self.assertEqual(0, self.run_main())

    def test_update_baseline_only_removes_entries(self):
        self.run_main('--reset-baseline')
        self.write('test/test_a.iec', _GOOD_TEST)
        self.write('test/test_b.iec', _BAD_TEST.replace('test_one', 'test_three'))
        self.assertEqual(1, self.run_main('--update-baseline'))
        self.assertEqual({'doc-language': [], 'test-fact': []}, self.read_baseline())

    def test_update_baseline_needs_an_existing_baseline(self):
        self.assertEqual(2, self.run_main('--update-baseline'))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'scripts', 'lint_baseline.json')))

    def test_update_baseline_creates_the_section_of_a_new_rule(self):
        self.write('scripts/lint_baseline.json', '{"doc-language": []}')
        self.assertEqual(0, self.run_main('--update-baseline'))
        self.assertEqual({'doc-language': [], 'test-fact': ['test/test_a.iec: test_one']},
                         self.read_baseline())

    def test_error_fails_even_with_a_baseline(self):
        self.run_main('--reset-baseline')
        self.write('test/test_c.iec', '/* c comment */\n')
        self.assertEqual(1, self.run_main())

    def test_paths_and_baseline_options_are_exclusive(self):
        self.assertEqual(2, self.run_main('--update-baseline',
                                          os.path.join(self.root, 'test')))

    def test_missing_path_is_an_error(self):
        self.assertEqual(2, self.run_main(os.path.join(self.root, 'no_such_dir')))

    def test_invalid_baseline_is_an_error(self):
        self.write('scripts/lint_baseline.json', '{')
        self.assertEqual(2, self.run_main())


@unittest.skipIf(shutil.which('git') is None, 'git is not available')
class CheckBaselineAgainstTest(unittest.TestCase):
    """Runs --check-baseline-against on a temporary git repository."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'scripts'))
        self.git('init', '-q')
        self.git('config', 'user.email', 'lint@example.com')
        self.git('config', 'user.name', 'lint')
        self.write('README', 'x\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'first')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def git(self, *args):
        subprocess.check_call(['git'] + list(args), cwd=self.root, stdout=subprocess.DEVNULL)

    def write(self, rel, text):
        with open(os.path.join(self.root, rel), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def write_baseline(self, data):
        self.write('scripts/lint_baseline.json', json.dumps(data))

    def check(self):
        return _quiet_main(['--check-baseline-against', 'HEAD'], self.root)

    def test_no_baseline_in_the_base_commit_is_skipped(self):
        self.write_baseline({'test-fact': ['a']})
        self.assertEqual(0, self.check())

    def test_missing_baseline_in_the_work_tree_fails(self):
        self.assertEqual(1, self.check())

    def test_added_entry_fails(self):
        self.write_baseline({'test-fact': ['a']})
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'baseline')
        self.write_baseline({'test-fact': ['a', 'b']})
        self.assertEqual(1, self.check())

    def test_removed_entry_and_new_rule_pass(self):
        self.write_baseline({'test-fact': ['a', 'b']})
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'baseline')
        self.write_baseline({'test-fact': ['a'], 'doc-language': ['x']})
        self.assertEqual(0, self.check())

    def test_unknown_commit_is_an_error(self):
        self.write_baseline({'test-fact': []})
        self.assertEqual(2, _quiet_main(['--check-baseline-against', 'no-such-commit'],
                                        self.root))


if __name__ == '__main__':
    unittest.main()
