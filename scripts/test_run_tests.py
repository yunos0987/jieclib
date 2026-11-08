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


class JudgeRunTest(unittest.TestCase):

    def test_exit_code_zero_and_a_passing_output_pass(self):
        ok, detail = run_tests.judge_run(0, _PASSED)
        self.assertTrue(ok, detail)

    def test_a_nonzero_exit_code_fails_even_with_a_passing_output(self):
        ok, detail = run_tests.judge_run(1, _PASSED)
        self.assertFalse(ok)
        self.assertIn('exited with code 1', detail[0])

    def test_a_nonzero_exit_code_keeps_the_reason_from_the_output(self):
        ok, detail = run_tests.judge_run(1, _PASSED + '[ FAILED ] a\n')
        self.assertFalse(ok)
        self.assertIn('exited with code 1', detail[0])
        self.assertIn('[ FAILED ]', detail[1])

    def test_exit_code_zero_does_not_hide_a_failing_output(self):
        self.assertFalse(run_tests.judge_run(0, _PASSED + '[ FAILED ] a\n')[0])


class PrintResultTest(unittest.TestCase):

    def printed(self, *args, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            run_tests._print_result(*args, **kwargs)
        return out.getvalue().splitlines()

    def test_a_run_line_shows_the_elapsed_seconds(self):
        lines = self.printed('run', 'test/a.iec', '-', True, ['2 ran, 2 passed, 0 skipped'], [],
                             12.34)
        self.assertEqual(1, len(lines))
        self.assertIn('test/a.iec  [12.3 s]  (2 ran, 2 passed, 0 skipped)', lines[0])

    def test_a_failed_run_line_shows_the_elapsed_seconds(self):
        lines = self.printed('run', 'test/a.iec', '-', False, ['timed out after 120s'], [],
                             120.04)
        self.assertTrue(lines[0].startswith('FAIL'))
        self.assertIn('test/a.iec  [120.0 s]', lines[0])
        self.assertIn('timed out after 120s', lines[1])

    def test_a_compile_line_has_no_seconds(self):
        lines = self.printed('compile', 'src/a.iec', 'omron', True, [], [])
        self.assertNotIn(' s]', lines[0])

    def test_main_prints_the_seconds_of_every_run(self):
        item = run_tests.Item('test/a.iec', 'test/a.iec', 'test', ['omron'])
        originals = (run_tests._select, run_tests._resolve_jiecc, run_tests.probe_run_options,
                     run_tests.run_item)
        run_tests._select = lambda root, items, paths: ([item], [])
        run_tests._resolve_jiecc = lambda explicit: 'jiecc'
        run_tests.probe_run_options = lambda jiecc, root, timeout: []
        run_tests.run_item = lambda *args: (True, ['1 ran, 1 passed, 0 skipped'])
        try:
            code, out = _quiet_main(['--run-only', 'test/a.iec'])
        finally:
            (run_tests._select, run_tests._resolve_jiecc, run_tests.probe_run_options,
             run_tests.run_item) = originals
        self.assertEqual(0, code, out)
        self.assertRegex(out, r'OK +run +- +test/a\.iec  \[\d+\.\d s\]')


class DiscoverTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_samples_with_a_header_are_discovered(self):
        _write(self.root, 'samples/s/s.iec', '(*\n * $ jiecc ./s.iec -o ./s.xml -t omron\n *)\n')
        _write(self.root, 'samples/s/part.iec', '// included by s.iec\n')
        names = [i.name for i in run_tests._discover(self.root)]
        self.assertIn('samples/s/s.iec', names)
        self.assertNotIn('samples/s/part.iec', names)

    def _write_aggregate(self):
        _write(self.root, 'test/c/a/test_a.iec', 'DEFINE_CONFIGURATION()\nTEST_S(test_a)\nEND_TEST_S\n')
        _write(self.root, 'test/c/b/test_b.iec', 'DEFINE_CONFIGURATION()\nTEST_S(test_b)\nEND_TEST_S\n')
        _write(self.root, 'test/c/test_c.iec',
               'DEFINE_CONFIGURATION()\n{#include "a/test_a.iec"}\n{#include "b/test_b.iec"}\n')

    def test_an_aggregate_lists_its_included_test_files(self):
        self._write_aggregate()
        items = {i.name: i for i in run_tests._discover(self.root)}
        self.assertEqual(2, len(items['test/c/test_c.iec'].included_tests))
        self.assertEqual((), items['test/c/a/test_a.iec'].included_tests)

    def test_a_file_with_its_own_test_is_not_an_aggregate(self):
        _write(self.root, 'test/c/a/test_a.iec', 'DEFINE_CONFIGURATION()\nTEST_S(test_a)\nEND_TEST_S\n')
        _write(self.root, 'test/c/test_c.iec',
               'DEFINE_CONFIGURATION()\n{#include "a/test_a.iec"}\nTEST_S(test_c)\nEND_TEST_S\n')
        items = {i.name: i for i in run_tests._discover(self.root)}
        self.assertEqual((), items['test/c/test_c.iec'].included_tests)

    def _run_main(self, selected_names):
        items = {i.name: i for i in run_tests._discover(self.root)}
        selected = [items[n] for n in selected_names]
        ran = []
        originals = (run_tests._select, run_tests._resolve_jiecc, run_tests.probe_run_options,
                     run_tests.run_item, run_tests._repo_root)
        run_tests._repo_root = lambda: self.root
        run_tests._select = lambda root, its, paths: (selected, [])
        run_tests._resolve_jiecc = lambda explicit: 'jiecc'
        run_tests.probe_run_options = lambda jiecc, root, timeout: []

        def fake_run_item(jiecc, root, item, *rest):
            ran.append(item.name)
            return True, ['1 ran, 1 passed, 0 skipped']
        run_tests.run_item = fake_run_item
        try:
            code, out = _quiet_main(['--run-only'])
        finally:
            (run_tests._select, run_tests._resolve_jiecc, run_tests.probe_run_options,
             run_tests.run_item, run_tests._repo_root) = originals
        return code, out, sorted(ran)

    def test_an_aggregate_is_not_run_when_its_files_run(self):
        self._write_aggregate()
        code, out, ran = self._run_main(['test/c/a/test_a.iec', 'test/c/b/test_b.iec',
                                         'test/c/test_c.iec'])
        self.assertEqual(0, code, out)
        self.assertEqual(['test/c/a/test_a.iec', 'test/c/b/test_b.iec'], ran)
        self.assertRegex(out, r'SKIP run +- +test/c/test_c\.iec  \(aggregate; its 2 included')
        self.assertIn('1 aggregate skipped', out)

    def test_an_aggregate_given_alone_is_run(self):
        self._write_aggregate()
        code, out, ran = self._run_main(['test/c/test_c.iec'])
        self.assertEqual(0, code, out)
        self.assertEqual(['test/c/test_c.iec'], ran)
        self.assertNotIn('SKIP', out)


class MainArgumentTest(unittest.TestCase):

    def test_output_dir_with_run_only_is_an_error(self):
        self.assertEqual(2, _quiet_main(['--run-only', '--output-dir', 'out'])[0])


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


# A JiecUnit test file with one test; BODY is replaced by the statements.
_TEST_FILE = textwrap.dedent('''\
    {#include <jiecunit.iec>}

    {#ifdef _TEST_}
    DEFINE_CONFIGURATION(
    \t_JIEC_TESTNAMES_LIST_(
    \t\ttest_sample
    \t)
    )
    {#endif}

    TEST_S(test_sample)
    \tvar
    \t\tn: dint;
    \tend
    \t// Fact: sample.
    BODY
    END_TEST_S
    ''')


@unittest.skipIf(_JIECC is None, 'jiecc is not found')
class RunItemTest(unittest.TestCase):
    """Runs test files outside the repository with jier (JiecUnit of vendor/jiecunit)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.dirname(_HERE)
        self.options = run_tests.probe_run_options(_JIECC, self.root, 60)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_body(self, body, timeout=120):
        text = _TEST_FILE.replace('BODY', body)
        path = _write(self.tmp, 'test_sample.iec', text)
        item = run_tests._make_item(self.root, path, text)
        self.assertEqual('test', item.kind)
        start = time.time()
        ok, detail = run_tests.run_item(_JIECC, self.root, item, 2000, timeout, self.options)
        return ok, detail, time.time() - start

    def test_a_passing_test_passes(self):
        ok, detail, _ = self.run_body('\tn := 1;\n\tEXPECT_EQ_DINT(1, n);')
        self.assertTrue(ok, detail)

    def test_a_failing_expect_fails(self):
        ok, detail, _ = self.run_body('\tn := 1;\n\tEXPECT_EQ_DINT(2, n);')
        self.assertFalse(ok)
        self.assertTrue(any('exited with code' in line or '[ FAILED ]' in line
                            for line in detail), detail)

    def test_a_test_that_never_finishes_is_killed_by_the_timeout(self):
        ok, detail, elapsed = self.run_body(
            '\tn := 0;\n\twhile n >= 0 do\n\t\tn := n mod 2;\n\tend_while;', timeout=10)
        self.assertFalse(ok)
        self.assertIn('timed out after 10s', detail[0])
        self.assertLess(elapsed, 60)


if __name__ == '__main__':
    unittest.main()
