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
        for rule in lint.SOURCE_RULES:
            names = os.listdir(os.path.join(_TESTDATA, rule))
            self.assertTrue(any(n.startswith('bad') for n in names), rule)
            self.assertTrue(any(n.startswith('good') for n in names), rule)

    def test_every_bad_input_has_an_expected_count(self):
        for rule in lint.SOURCE_RULES:
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
        for rule in lint.SOURCE_RULES:
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


_XML_DATA = os.path.join(_TESTDATA, 'xml')
_XML_OUT = os.path.join(_XML_DATA, 'out')
_BOTH = ['omron', 'keyence']

# (rule, key) of every finding that bad_xml.iec must produce.
_XML_EXPECTED = {
    ('no-alias-type', 'Bad_count_t'),
    ('omron-p-prefix', 'Bad_record_t.p_value'),
    ('reserved-name', 'Bad_record_t.left'),
    ('keyence-names', 'Bad_record_t.v'),
    ('no-struct-return', 'Bad_returns_struct'),
    ('varlen-array-inout', 'Bad_returns_struct.values'),
    ('keyence-names', 'Bad_returns_struct.x'),
    ('keyence-names', 'Bad_returns_struct.hi'),
    ('keyence-names', 'Bad_returns_struct.r1'),
    ('reserved-name', 'Bad_returns_struct.cmp'),
    ('omron-p-prefix', 'Bad_returns_struct.P_count'),
    ('pou-name-length', 'Bad_function_block_whose_name_is_longer_than_sixty_four_bytes_xxx'),
    ('varlen-array-inout', 'Bad_function_block_whose_name_is_longer_than_sixty_four_bytes_xxx.arr'),
}


def _xml_keys(findings):
    return set((f.rule, f.key) for f in findings)


def _find_jiecc():
    found = os.environ.get('JIECC') or shutil.which('jiecc') or shutil.which('jiecc.exe')
    return found if found and (os.path.isfile(found) or shutil.which(found)) else None


class XmlRuleTest(unittest.TestCase):
    """The XML rules, on XML compiled from scripts/lint_testdata/xml/*.iec."""

    def check(self, name, targets=None, pous=(), types=(), xml_dir=_XML_OUT):
        return lint.lint_xml.check_xml_dir(xml_dir, [(name, targets or _BOTH)], set(pous),
                                           set(types))

    def test_every_xml_rule_is_covered(self):
        rules = set(rule for rule, key in _XML_EXPECTED) | {'xml-missing'}
        self.assertEqual(set(r for r, s in lint.lint_xml.RULES), rules)

    def test_bad_input(self):
        self.assertEqual(_XML_EXPECTED, _xml_keys(self.check('bad_xml.iec')))

    def test_good_input(self):
        self.assertEqual([], [f.format() for f in self.check('good_xml.iec')])

    def test_keyence_names_only_for_keyence_and_mitsubishi(self):
        keys = _xml_keys(self.check('bad_xml.iec', ['omron']))
        self.assertEqual(set(k for k in _XML_EXPECTED if k[0] != 'keyence-names'), keys)

    def test_severity_and_format(self):
        findings = dict(((f.rule, f.key), f) for f in self.check('bad_xml.iec'))
        f = findings[('keyence-names', 'Bad_returns_struct.x')]
        self.assertEqual('warning', f.severity)
        self.assertTrue(f.format().endswith(
            'keyence/bad_xml.xml: warning: keyence-names: Bad_returns_struct.x: '
            'one-letter name (KEYENCE / Mitsubishi naming rule)'), f.format())
        self.assertEqual('error', findings[('reserved-name', 'Bad_record_t.left')].severity)

    def test_jiecunit_names_are_not_checked(self):
        keys = _xml_keys(self.check('bad_xml.iec', pous=['bad_returns_struct'],
                                    types=['bad_record_t', 'bad_count_t']))
        self.assertEqual(
            {('pou-name-length',
              'Bad_function_block_whose_name_is_longer_than_sixty_four_bytes_xxx'),
             ('varlen-array-inout',
              'Bad_function_block_whose_name_is_longer_than_sixty_four_bytes_xxx.arr')}, keys)

    def test_missing_and_broken_xml_are_errors(self):
        keys = [f.rule for f in self.check('bad_xml.iec', ['mitsubishi'])]
        self.assertEqual(['xml-missing'], keys)
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, 'omron'))
            with open(os.path.join(tmp, 'omron', 'x.xml'), 'w') as f:
                f.write('<Project')
            findings = self.check('x.iec', ['omron'], xml_dir=tmp)
            self.assertEqual(['xml-missing'], [f.rule for f in findings])
            self.assertIn('cannot read', findings[0].message)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_source_names(self):
        code = ('type\n\tA_t: struct\n\t\tx: dint;\n\tend_struct;\n\tB_t: dint;\nend_type\n'
                'function F1: dint\nend_function\nfunction_block Fb2\nend_function_block\n')
        self.assertEqual(({'f1', 'fb2'}, {'a_t', 'x', 'b_t'}), lint.lint_xml.source_names(code))

    @unittest.skipIf(_find_jiecc() is None, 'jiecc is not found')
    def test_committed_xml_matches_jiecc(self):
        # The XML in lint_testdata/xml/out is committed so that the lint job
        # (without jiecc) can test the rules. Recompile it and compare the
        # findings, to notice a change of the XML format of jiecc.
        jiecc = _find_jiecc()
        tmp = tempfile.mkdtemp()
        try:
            for name in ('bad_xml', 'good_xml'):
                for target in _BOTH:
                    os.makedirs(os.path.join(tmp, target), exist_ok=True)
                    subprocess.check_call(
                        [jiecc, name + '.iec', '-o', os.path.join(tmp, target, name + '.xml'),
                         '-t', target], cwd=_XML_DATA, stdout=subprocess.DEVNULL)
                self.assertEqual(_xml_keys(self.check(name + '.iec')),
                                 _xml_keys(self.check(name + '.iec', xml_dir=tmp)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


_HEADER_BOTH = '(*\n * $ jiecc ./a.iec -o ./a.xml -t omron\n * $ jiecc ./a.iec -o ./a.xml -t keyence\n *)\n'


class MainXmlTest(unittest.TestCase):
    """Runs main() with --xml-dir on a temporary repository."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rel in ('src/a', 'scripts', 'out/omron/src/a', 'out/keyence/src/a'):
            os.makedirs(os.path.join(self.root, *rel.split('/')))
        self.write('src/a/a.iec', _HEADER_BOTH + '(*{doc A.}*)\nfunction F1: dint\n\tF1 := 1;\nend\n')
        self.out = os.path.join(self.root, 'out')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        with open(os.path.join(self.root, *rel.split('/')), 'w', encoding='utf-8',
                  newline='\n') as f:
            f.write(text)

    def use_xml(self, name):
        for target in _BOTH:
            shutil.copyfile(os.path.join(_XML_OUT, target, name),
                            os.path.join(self.out, target, 'src', 'a', 'a.xml'))

    def read_baseline(self):
        with open(os.path.join(self.root, 'scripts', 'lint_baseline.json'), encoding='utf-8') as f:
            return json.load(f)

    def run_main(self, *argv):
        return _quiet_main(list(argv), self.root)

    def test_good_xml_passes_and_missing_xml_fails(self):
        self.assertEqual(1, self.run_main('--xml-dir', self.out))
        self.use_xml('good_xml.xml')
        self.assertEqual(0, self.run_main('--xml-dir', self.out))
        self.assertEqual(2, self.run_main('--xml-dir', os.path.join(self.root, 'none')))

    def test_keyence_names_baseline(self):
        self.use_xml('bad_xml.xml')
        self.assertEqual(1, self.run_main('--xml-dir', self.out))
        # The baseline is written, but the errors still fail: only warnings
        # can be in the baseline.
        self.assertEqual(1, self.run_main('--reset-baseline', '--xml-dir', self.out))
        self.assertEqual(4, len(self.read_baseline()['keyence-names']))
        self.assertEqual(1, self.run_main('--xml-dir', self.out))
        # Without --xml-dir, the keyence-names section is kept as it is.
        self.assertEqual(0, self.run_main('--update-baseline'))
        self.assertEqual(4, len(self.read_baseline()['keyence-names']))
        self.assertEqual(0, self.run_main())
        # With --xml-dir, fixed warnings are removed from the baseline.
        self.use_xml('good_xml.xml')
        self.assertEqual(0, self.run_main('--update-baseline', '--xml-dir', self.out))
        self.assertEqual([], self.read_baseline()['keyence-names'])

    def test_baseline_is_not_rewritten_when_an_xml_is_missing(self):
        self.use_xml('bad_xml.xml')
        self.run_main('--reset-baseline', '--xml-dir', self.out)
        before = self.read_baseline()
        os.remove(os.path.join(self.out, 'keyence', 'src', 'a', 'a.xml'))
        self.assertEqual(2, self.run_main('--update-baseline', '--xml-dir', self.out))
        self.assertEqual(2, self.run_main('--reset-baseline', '--xml-dir', self.out))
        self.assertEqual(before, self.read_baseline())

    def test_paths_limit_the_expected_xml(self):
        self.write('src/b.iec', '(*\n * $ jiecc ./b.iec -o ./b.xml -t omron\n *)\n'
                   '(*{doc B.}*)\nfunction F2: dint\n\tF2 := 2;\nend\n')
        self.use_xml('good_xml.xml')
        # src/b.iec has no XML: a full run fails, a run on src/a passes.
        self.assertEqual(1, self.run_main('--xml-dir', self.out))
        old = os.getcwd()
        os.chdir(self.root)
        try:
            self.assertEqual(0, self.run_main('--xml-dir', self.out, 'src/a'))
        finally:
            os.chdir(old)


if __name__ == '__main__':
    unittest.main()
