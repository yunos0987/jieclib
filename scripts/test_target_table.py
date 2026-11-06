#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/target_table.py and the target-consistency rule of lint.py.

Usage:
  python scripts/test_target_table.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import lint  # noqa: E402
import target_table  # noqa: E402


def _header(*targets):
    return '(*\n' + ''.join(' * $ jiecc ./x.iec -o ./x.xml -t {}\n'.format(t) for t in targets) + ' *)\n'


class TargetTableTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.write('src/alpha/alpha.iec', _header('omron', 'keyence'))
        self.write('src/alpha/alpha_template.iec', '// no header\n')
        self.write('test/alpha/test_alpha.iec', _header('omron', 'keyence') + 'DEFINE_CONFIGURATION\n')
        self.write('src/beta/beta_template.iec', '// only a template\n')
        self.write('test/beta/test_beta.iec', _header('omron', 'keyence') + 'DEFINE_CONFIGURATION\n')
        self.write('src/sys.iec', '// no header\n')
        self.write('test/test_sys.iec', _header('omron') + 'DEFINE_CONFIGURATION\n')
        self.write('README.md', 'x\n' + target_table.BEGIN + '\nold\n' + target_table.END + '\ny\n')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            return target_table.main(list(argv), root=self.root), out.getvalue()

    def test_object_of(self):
        self.assertEqual('alpha', target_table.object_of('src/alpha/x/y.iec'))
        self.assertEqual('sys', target_table.object_of('test/test_sys.iec'))
        self.assertEqual('', target_table.object_of('samples/a/a.iec'))

    def test_render_uses_the_tests_when_the_sources_have_no_header(self):
        table = target_table.render(self.root)
        self.assertIn('| [alpha](./src/alpha) | keyence, omron |', table)
        self.assertIn('| [beta](./src/beta) | keyence, omron |', table)
        self.assertIn('（`src/` 直下の `sys.iec` など） | omron |', table)
        self.assertEqual([], target_table.mismatches(self.root))

    def test_check_and_update(self):
        self.assertEqual(1, self.run_main('--check')[0])
        self.assertEqual(0, self.run_main('--update')[0])
        self.assertEqual(0, self.run_main('--check')[0])
        with open(os.path.join(self.root, 'README.md'), encoding='utf-8') as f:
            text = f.read()
        self.assertTrue(text.startswith('x\n' + target_table.BEGIN + '\n| ライブラリ'))
        self.assertTrue(text.endswith(target_table.END + '\ny\n'))

    def test_missing_markers_are_an_error(self):
        self.write('README.md', 'no table\n')
        self.assertEqual(1, self.run_main('--check')[0])

    def test_a_test_without_a_header_declares_omron(self):
        # run_tests.py compiles a test without a header for omron, so it
        # does not agree with sources that declare keyence too.
        self.write('test/alpha/test_alpha.iec', 'DEFINE_CONFIGURATION\n')
        self.assertEqual([('alpha', ['keyence', 'omron'], ['omron'])], target_table.mismatches(self.root))

    def test_mismatch_is_a_lint_error(self):
        self.write('test/alpha/test_alpha.iec', _header('omron') + 'DEFINE_CONFIGURATION\n')
        self.assertEqual([('alpha', ['keyence', 'omron'], ['omron'])], target_table.mismatches(self.root))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = lint.main([], root=self.root)
        self.assertEqual(1, code)
        self.assertIn('src/alpha:1: error: target-consistency:', out.getvalue())
        # With paths, the rule on the whole repository is not checked.
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = lint.main([os.path.join(self.root, 'src', 'alpha', 'alpha.iec')], root=self.root)
        self.assertEqual(0, code)
        self.assertNotIn('target-consistency', out.getvalue())


if __name__ == '__main__':
    unittest.main()
