#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/run_tests.py.

The tests that call jiecc are skipped when jiecc is not found (--jiecc is
not used here; JIECC or PATH is).

Usage:
  python scripts/test_run_tests.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import run_tests  # noqa: E402


def _find_jiecc():
    found = os.environ.get('JIECC') or shutil.which('jiecc') or shutil.which('jiecc.exe')
    return found if found and run_tests._is_executable_path(found) else None


_JIECC = _find_jiecc()

_PASSED = textwrap.dedent('''\
    [========] Running 2 tests.
    [ RUN    ] a
    [     OK ] a (0us)
    [ RUN    ] b
    [     OK ] b (0us)
    [========] 2 tests ran. (0us)
    [ PASSED ] 2 tests.
    ''')


def _write(root, rel, text):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return path


def _quiet_main(argv):
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(out):
        code = run_tests.main(argv)
    return code, out.getvalue()


class JudgeRunOutputTest(unittest.TestCase):

    def test_passed(self):
        ok, detail = run_tests.judge_run_output(_PASSED)
        self.assertTrue(ok, detail)

    def test_no_summary_is_a_failure(self):
        # This is what jier prints when the cycles run out.
        ok, detail = run_tests.judge_run_output('[========] Running 1 tests.\n[ RUN    ] a\n')
        self.assertFalse(ok)
        self.assertIn('too few cycles', detail[0])

    def test_fewer_tests_ran_than_registered_is_a_failure(self):
        text = _PASSED.replace('Running 2 tests', 'Running 3 tests')
        ok, detail = run_tests.judge_run_output(text)
        self.assertFalse(ok)
        self.assertIn('3 were registered', detail[0])

    def test_no_running_line_is_a_failure(self):
        text = _PASSED.replace('[========] Running 2 tests.\n', '')
        self.assertFalse(run_tests.judge_run_output(text)[0])

    def test_failed_and_error_lines(self):
        for line in ('[ FAILED ] a', '[  ERROR ] a', 'error: something', 'InterpreterFault'):
            with self.subTest(line=line):
                self.assertFalse(run_tests.judge_run_output(_PASSED + line + '\n')[0])


class PathsFileTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        _write(self.root, 'src/a/a.iec', '(*\n * $ jiecc ./a.iec -o ./a.xml -t omron\n *)\n')
        _write(self.root, 'src/a/a_template.iec', '// no header\n')
        _write(self.root, 'test/a/test_a.iec', 'DEFINE_CONFIGURATION\n')
        _write(self.root, 'test/a/test_b.iec', 'DEFINE_CONFIGURATION\n')
        self.items = run_tests._discover(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def select(self, text, need_tests=True):
        path = _write(self.root, 'paths.txt', text)
        return run_tests._select_from_file(self.root, self.items, path, need_tests)

    def test_paths_and_cycles(self):
        items, cycles, errors = self.select(
            '# comment\n\n  test/a/test_a.iec 1000\ntest/a/test_b.iec\n')
        self.assertEqual([], errors)
        self.assertEqual(['test/a/test_a.iec', 'test/a/test_b.iec'], [i.name for i in items])
        self.assertEqual({'test/a/test_a.iec': 1000}, cycles)

    def test_directory_selects_its_files(self):
        items, cycles, errors = self.select('test/a 500\n')
        self.assertEqual([], errors)
        self.assertEqual(2, len(items))
        self.assertEqual({'test/a/test_a.iec': 500, 'test/a/test_b.iec': 500}, cycles)

    def test_bom_is_ignored(self):
        items, cycles, errors = self.select('\ufeff# comment\ntest/a/test_a.iec\n')
        self.assertEqual([], errors)
        self.assertEqual(['test/a/test_a.iec'], [i.name for i in items])

    def test_only_comments_selects_nothing(self):
        self.assertEqual(([], {}, []), self.select('# nothing yet\n'))

    def test_errors(self):
        cases = {
            'test\\a\\test_a.iec\n': 'use "/"',
            'test/a/missing.iec\n': 'no such file',
            'test/a/test_a.iec 0\n': 'positive integer',
            'test/a/test_a.iec x\n': 'positive integer',
            'test/a/test_a.iec 1 2\n': 'expected',
            'test/a/test_a.iec\ntest/a/test_a.iec\n': 'already listed',
            'test/a\ntest/a/test_a.iec\n': 'already selected',
            '/test/a/test_a.iec\n': 'relative',
            'src/a/a.iec\n': 'has no test file',
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                items, cycles, errors = self.select(text)
                self.assertEqual(1, len(errors), errors)
                self.assertIn(message, errors[0])

    def test_source_file_is_allowed_when_only_compiling(self):
        items, cycles, errors = self.select('src/a/a.iec\n', need_tests=False)
        self.assertEqual([], errors)
        self.assertEqual(['src/a/a.iec'], [i.name for i in items])

    def test_samples_with_a_header_are_discovered(self):
        _write(self.root, 'samples/s/s.iec', '(*\n * $ jiecc ./s.iec -o ./s.xml -t omron\n *)\n')
        _write(self.root, 'samples/s/part.iec', '// included by s.iec\n')
        names = [i.name for i in run_tests._discover(self.root)]
        self.assertIn('samples/s/s.iec', names)
        self.assertNotIn('samples/s/part.iec', names)

    def test_missing_file(self):
        entries, errors = run_tests.read_paths_file(os.path.join(self.root, 'none.txt'))
        self.assertEqual([], entries)
        self.assertIn('cannot read', errors[0])


class MainArgumentTest(unittest.TestCase):

    def test_output_dir_with_run_only_is_an_error(self):
        self.assertEqual(2, _quiet_main(['--run-only', '--output-dir', 'out'])[0])

    def test_paths_and_paths_from_together_are_an_error(self):
        self.assertEqual(2, _quiet_main(['--paths-from', 'x.txt', 'src'])[0])

    def test_empty_paths_file_passes(self):
        tmp = tempfile.mkdtemp()
        try:
            path = _write(tmp, 'paths.txt', '# no tests yet\n')
            code, out = _quiet_main(['--run-only', '--paths-from', path])
            self.assertEqual(0, code, out)
            self.assertIn('nothing to check', out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bad_paths_file_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            path = _write(tmp, 'paths.txt', 'test/no/such_file.iec\n')
            self.assertEqual(2, _quiet_main(['--run-only', '--paths-from', path])[0])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_jier_required_file_is_valid(self):
        path = os.path.join(_HERE, 'jier_required.txt')
        entries, errors = run_tests.read_paths_file(path)
        self.assertEqual([], errors)


class XmlPathTest(unittest.TestCase):

    def test_kept_path_mirrors_the_repository(self):
        item = run_tests.Item('src/string_lib/string_lib.iec', 'src/string_lib/string_lib.iec',
                              'src', ['omron'])
        self.assertEqual(os.path.join('out', 'keyence', 'src', 'string_lib', 'string_lib.xml'),
                         run_tests.xml_path('out', item, 'keyence', True))

    def test_temporary_path_is_flat(self):
        item = run_tests.Item('test/math/test_floor.iec', 'test/math/test_floor.iec',
                              'test', ['omron'])
        self.assertEqual(os.path.join('tmp', 'test_math_test_floor.iec.omron.xml'),
                         run_tests.xml_path('tmp', item, 'omron', False))


# A child that starts a grandchild sharing its output, as jiecc.exe does. The
# grandchild writes a marker file if it is still alive after a few seconds.
_TREE_SCRIPT = textwrap.dedent('''\
    import subprocess, sys, time
    marker = sys.argv[1]
    code = "import time, sys; time.sleep(6); open(sys.argv[1], 'w').close()"
    subprocess.Popen([sys.executable, '-c', code, marker])
    print('started', flush=True)
    time.sleep(60)
    ''')


class RunOptionsTest(unittest.TestCase):

    def test_allow_narrowing_is_passed_when_help_lists_it(self):
        help_text = 'usage: jiecc ...\n  --allow-narrowing  under fail, ...\n'
        self.assertEqual(['--allow-narrowing'], run_tests.run_options_from_help(help_text))

    def test_nothing_is_passed_when_help_does_not_list_it(self):
        self.assertEqual([], run_tests.run_options_from_help('usage: jiecc ...\n  --run\n'))
        self.assertEqual([], run_tests.run_options_from_help(''))

    def test_run_item_appends_the_options(self):
        item = run_tests.Item('x', os.path.join('test', 'x', 'x.iec'), 'test', ['omron'])
        seen = []

        def fake_execute(cmd, cwd, timeout):
            seen.append(cmd)
            return None, 'not run'

        original = run_tests._execute
        run_tests._execute = fake_execute
        try:
            run_tests.run_item('jiecc', _HERE, item, 5, 1, ['--allow-narrowing'])
            run_tests.run_item('jiecc', _HERE, item, 5, 1)
        finally:
            run_tests._execute = original
        self.assertEqual('--allow-narrowing', seen[0][-1])
        self.assertEqual(['--max-cycles', '5'], seen[0][-3:-1])
        self.assertEqual(['--max-cycles', '5'], seen[1][-2:])

    def test_a_failed_help_gives_no_options(self):
        self.assertEqual([], run_tests.probe_run_options(
            os.path.join(_HERE, 'no_such_jiecc.exe'), _HERE, 5))

    @unittest.skipIf(_JIECC is None, 'jiecc is not found')
    def test_the_installed_jiecc_is_probed(self):
        code, output = run_tests._execute([_JIECC, '--help'], _HERE, 60)
        self.assertEqual(0, code)
        self.assertEqual(run_tests.run_options_from_help(output),
                         run_tests.probe_run_options(_JIECC, _HERE, 60))


class TimeoutTest(unittest.TestCase):

    def test_timeout_kills_the_process_tree(self):
        tmp = tempfile.mkdtemp()
        try:
            script = _write(tmp, 'tree.py', _TREE_SCRIPT)
            marker = os.path.join(tmp, 'still_alive')
            start = time.time()
            code, message = run_tests._execute([sys.executable, script, marker], tmp, 2)
            elapsed = time.time() - start
            self.assertIsNone(code)
            self.assertIn('the process tree was killed', message)
            # Returning at all means the output pipe was closed, that is, the
            # grandchild has ended too.
            self.assertLess(elapsed, 20)
            time.sleep(8)
            self.assertFalse(os.path.exists(marker), 'the grandchild survived the timeout')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_normal_exit(self):
        code, output = run_tests._execute([sys.executable, '-c', 'print(42)'], _HERE, 30)
        self.assertEqual(0, code)
        self.assertEqual('42', output.strip())


@unittest.skipIf(_JIECC is None, 'jiecc is not found')
class CompileItemTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmp, 'out')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def compile(self, text):
        path = _write(self.tmp, 'x/sample.iec', text)
        item = run_tests.Item('x/sample.iec', path, 'src', ['omron'])
        ok, detail, warnings = run_tests.compile_item(
            _JIECC, self.tmp, item, 'omron', self.outdir, 120, keep=True)
        return ok, detail, os.path.join(self.outdir, 'omron', 'x', 'sample.xml')

    def test_success_keeps_the_xml(self):
        ok, detail, xml = self.compile(
            '(*{doc Returns one.}*)\nfunction One: dint\n\tOne := 1;\nend_function\n')
        self.assertTrue(ok, detail)
        self.assertTrue(os.path.isfile(xml))

    def test_failure_removes_the_xml(self):
        xml = os.path.join(self.outdir, 'omron', 'x', 'sample.xml')
        _write(self.tmp, 'out/omron/x/sample.xml', 'stale')
        ok, detail, xml = self.compile('function Broken: dint\n\tBroken := ;\nend_function\n')
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(xml))


if __name__ == '__main__':
    unittest.main()
