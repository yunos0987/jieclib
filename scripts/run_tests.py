#!/usr/bin/env python
# coding: utf-8
"""Compile and run the JiecLib sources and tests with jiecc.

Compile phase:
  - Every source entry file under src/ and every example under samples/ (a
    file whose header comment has a "$ jiecc" command line) and every test
    file under test/ that contains
    DEFINE_CONFIGURATION is compiled for each target named by "-t <target>"
    on the "$ jiecc" lines of its header comment (OMRON when none is named).
  - Include paths are the repository root, src and vendor/jiecunit.
    Test files are compiled with -D_TEST_.
  - The XML output goes to a temporary directory, never into the repository,
    unless --output-dir DIR is given. Then it is kept as
    DIR/<target>/<path of the file>.xml with .iec replaced by .xml (for
    example DIR/omron/src/string_lib/string_lib.xml). The XML of a failed
    compile is removed. Old files in DIR are not removed.
  - A compile fails when jiecc exits with a nonzero code or prints an
    "error: " line. Warnings are printed but do not fail the check.

Run phase:
  - Every test file is interpreted with the jier interpreter
    (`jiecc --run ... -D_TEST_ --max-cycles N`). When `jiecc --help` lists
    --allow-narrowing (Jiecc 9.4.0 and later), it is added: the sources
    convert the UINT that the OMRON LEN returns with `uint_to_dint(len(s))`,
    and jier's len returns a DINT, so without it jier stops at that
    narrowing (its --type-check defaults to fail).
  - Since JiecUnit v7.0.0, JiecUnitMain calls halt after it prints the
    summary, so `jiecc --run` ends as soon as the tests have finished, and
    its exit code is 0 when all tests pass and 1 otherwise. A run passes only
    when jiecc exits with 0, the summary is printed, the number of tests in
    the summary equals the number in the "[========] Running N tests." line,
    no "[ FAILED ]" or "[  ERROR ]" line is printed, and no "error: " or
    "InterpreterFault" line is printed.
  - The result line of each run shows its elapsed seconds ("[12.3 s]"). A
    test file should finish within 60 s under jier; a slower one reduces
    its work under {#ifdef _JIER}.
  - An aggregate test file (no TEST_S / TEST_M of its own; it includes test
    files with {#include "..."}, such as test/container/test_container.iec)
    is compiled but not run when every test file it includes is run too;
    a "SKIP run" line names it. Given alone, it is run.
  - --max-cycles is a safety cap for a program that never reaches the halt.
    When jier stops at the cap, the summary is not printed or counts fewer
    tests, and the run fails.

Timeout:
  - jiecc.exe starts a child process that does the work. When a compile or
    a run takes longer than --timeout seconds (for example a test that never
    finishes a cycle), the whole process tree is killed (taskkill /T on
    Windows, the process group elsewhere), and the check fails.

The jiecc executable is looked up in this order: --jiecc PATH, the JIECC
environment variable, then jiecc on PATH.

Usage:
  python scripts/run_tests.py
  python scripts/run_tests.py --jiecc /path/to/jiecc.exe
  python scripts/run_tests.py --compile-only
  python scripts/run_tests.py --compile-only --output-dir out src/string_lib
  python scripts/run_tests.py --run-only test/math/test_floor.iec
  python scripts/run_tests.py src/array test/array --jobs 4
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

_DEFAULT_TARGET = 'omron'
# A safety cap: the tests halt jier when they have finished (JiecUnit v7.0.0).
_DEFAULT_MAX_CYCLES = 2000
# Kills a compile or run that does not end (for example a loop that never
# finishes a cycle). A test file should take 60 s or less under jier when run
# alone (AGENTS.md); with --jobs equal to the CPU count, a run takes 2 to 3
# times as long as alone, so the limit is well above 60 s. The run line of
# each test file shows its seconds.
_DEFAULT_TIMEOUT = 300
# Seconds to wait for the output pipe to close after the process tree is killed.
_DRAIN_TIMEOUT = 30

_RE_RUNNING = re.compile(r'^\[========\] Running (\d+) tests\.')
_RE_TESTS_RAN = re.compile(r'^\[========\] (\d+) tests ran\.')
_RE_PASSED = re.compile(r'^\[ PASSED \] (\d+) tests\.')
_RE_SKIPPED = re.compile(r'^\[ SKIPPED\] (\d+) tests\.')
_RE_FAILED_LINE = re.compile(r'\[ FAILED \]')
_RE_ERROR_LINE = re.compile(r'\[  ERROR \]')
# jiecc can print an "error: " line while still exiting 0, so the output text
# is scanned regardless of the process exit code.
_RE_ERROR_TEXT = re.compile(r'(?m)(?:^|\s)error: ')
_RE_WARNING_TEXT = re.compile(r'(?i)\bwarning\b')
_RE_FAULT_TEXT = re.compile(r'InterpreterFault')
_RE_JIECC_LINE = re.compile(r'\$\s*jiecc\b')
_RE_TARGET = re.compile(r'(?:^|\s)(?:-t|--target)[ =]?([A-Za-z_]+)')


def _repo_root():
    # type: () -> str
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_executable_path(path):
    # type: (str) -> bool
    return os.path.isfile(path) or shutil.which(path) is not None


def _resolve_jiecc(explicit):
    # type: (str) -> str
    if explicit:
        if _is_executable_path(explicit):
            return explicit
        print('error: jiecc executable not found at {!r} (from --jiecc).'.format(explicit),
              file=sys.stderr)
        sys.exit(2)
    from_env = os.environ.get('JIECC')
    if from_env:
        if _is_executable_path(from_env):
            return from_env
        print('error: jiecc executable not found at {!r} '
              '(from the JIECC environment variable).'.format(from_env),
              file=sys.stderr)
        sys.exit(2)
    found = shutil.which('jiecc') or shutil.which('jiecc.exe')
    if found:
        return found
    print('error: jiecc executable not found. '
          'Specify it with --jiecc PATH, set the JIECC environment variable, '
          'or add jiecc to PATH.',
          file=sys.stderr)
    sys.exit(2)


def _native_path(path):
    # type: (str) -> str
    """Return a path that a Windows-native jiecc.exe understands.

    Under Cygwin's own Python, absolute paths look like /tmp/...; convert them
    with cygpath. Elsewhere the path is returned unchanged.
    """
    if sys.platform != 'cygwin' or not os.path.isabs(path):
        return path
    try:
        return subprocess.check_output(['cygpath', '-w', path]).decode('utf-8').strip()
    except (OSError, subprocess.CalledProcessError):
        return path


def _read_text(path):
    # type: (str) -> str
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def _header_comment(text):
    # type: (str) -> str
    """Return the leading (* ... *) comment of a file, or '' if there is none."""
    stripped = text.lstrip()
    if not stripped.startswith('(*'):
        return ''
    end = stripped.find('*)')
    return stripped if end < 0 else stripped[:end]


def _header_targets(text):
    # type: (str) -> list
    """Return the targets named on the "$ jiecc" lines of the header comment."""
    targets = []
    for line in _header_comment(text).splitlines():
        if not _RE_JIECC_LINE.search(line):
            continue
        for m in _RE_TARGET.finditer(line):
            name = m.group(1).lower()
            if name not in targets:
                targets.append(name)
    return targets


def _has_jiecc_line(text):
    # type: (str) -> bool
    return any(_RE_JIECC_LINE.search(line) for line in _header_comment(text).splitlines())


class Item(object):
    """A file to check.

    name is the repository-relative path with "/" (or the given path for a
    file outside the repository), path is the argument passed to jiecc, kind
    is 'src' or 'test', and in_repo tells whether the file is in the
    repository. included_tests lists the normalized absolute paths of the
    test files that an aggregate test file includes (see _included_tests);
    it is empty for any other file.
    """

    def __init__(self, name, path, kind, targets, in_repo=True, included_tests=()):
        # type: (str, str, str, list, bool, tuple) -> None
        self.name = name
        self.path = path
        self.kind = kind
        self.targets = targets
        self.in_repo = in_repo
        self.included_tests = tuple(included_tests)


_RE_TEST_DEFINITION = re.compile(r'^\s*TEST_[SM]\(', re.MULTILINE)
_RE_LOCAL_INCLUDE = re.compile(r'^\s*\{#include\s+"([^"]+)"\}', re.MULTILINE)


def _included_tests(path, text):
    # type: (str, str) -> list
    """Return the test files that an aggregate test file includes.

    An aggregate test file (for example test/container/test_container.iec)
    defines no TEST_S / TEST_M of its own and includes, with
    {#include "..."}, test files that contain DEFINE_CONFIGURATION. The
    result holds their normalized absolute paths; it is empty for a file
    that defines a test or includes no test file.
    """
    if _RE_TEST_DEFINITION.search(text):
        return []
    found = []
    for rel in _RE_LOCAL_INCLUDE.findall(text):
        included = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(path)), rel))
        if os.path.isfile(included) and 'DEFINE_CONFIGURATION' in _read_text(included):
            found.append(os.path.normcase(included))
    return found


def _make_item(root, path, text):
    # type: (str, str, str) -> Item
    rel = os.path.relpath(path, root)
    in_repo = not (rel.startswith('..') or os.path.isabs(rel))
    if in_repo:
        name = rel.replace(os.sep, '/')
        arg = name
    else:
        name = path
        arg = _native_path(path)
    kind = 'test' if 'DEFINE_CONFIGURATION' in text else 'src'
    targets = _header_targets(text) or [_DEFAULT_TARGET]
    included = _included_tests(path, text) if kind == 'test' else []
    return Item(name, arg, kind, targets, in_repo, included)


def _discover(root):
    # type: (str) -> list
    items = []
    # samples/ holds usage examples; like src/, a file is compiled when its
    # header has a "$ jiecc" line.
    for top, kind in (('src', 'src'), ('test', 'test'), ('samples', 'src')):
        base = os.path.join(root, top)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for filename in sorted(filenames):
                if not filename.endswith('.iec'):
                    continue
                path = os.path.join(dirpath, filename)
                text = _read_text(path)
                if kind == 'src' and not _has_jiecc_line(text):
                    continue
                if kind == 'test' and 'DEFINE_CONFIGURATION' not in text:
                    continue
                items.append(_make_item(root, path, text))
    return items


def _select_one(root, by_path, raw):
    # type: (str, dict, str) -> tuple
    """Return (items selected by one path, error or None)."""
    path = os.path.abspath(raw)
    key = os.path.normcase(path)
    if os.path.isdir(path):
        prefix = key.rstrip(os.sep) + os.sep
        matched = [item for k, item in sorted(by_path.items()) if k.startswith(prefix)]
        if not matched:
            return [], '{}: no source entry file or test file in this directory'.format(raw)
        return matched, None
    if os.path.isfile(path):
        item = by_path.get(key)
        if item is None:
            item = _make_item(root, path, _read_text(path))
            by_path[key] = item
        return [item], None
    return [], '{}: no such file or directory'.format(raw)


def _select(root, items, filters):
    # type: (str, list, list) -> tuple
    """Filter the discovered items by the given paths.

    A directory selects the discovered files below it. A file selects itself;
    a file that is not one of the discovered files (for example a file outside
    the repository) is checked as a source file, or as a test file when it
    contains DEFINE_CONFIGURATION. Returns (items, errors).
    """
    if not filters:
        return items, []
    by_path = {os.path.normcase(os.path.join(root, item.name)): item for item in items}
    selected = []
    errors = []
    for raw in filters:
        matched, error = _select_one(root, by_path, raw)
        if error:
            errors.append(error)
        for item in matched:
            if item not in selected:
                selected.append(item)
    return selected, errors


def _common_args(root, item):
    # type: (str, Item) -> list
    args = ['-I.', '-I./src', '-I./vendor/jiecunit']
    if item.kind == 'test':
        args.append('-D_TEST_')
    return args


# jier (jiecc --run) stops at a type mismatch by default since Jiecc 9.4.0
# (--type-check=fail). The OMRON LEN returns a UINT, so the sources write
# `uint_to_dint(len(s))`; jier's own len returns a DINT, which makes that
# argument a DINT -> UINT narrowing. --allow-narrowing turns a narrowing
# inside one family (integer -> integer) back into a warning. Older jiecc
# does not know the option, so it is passed only when `jiecc --help` lists
# it.
_RUN_OPTIONS_IF_SUPPORTED = ['--allow-narrowing']


def run_options_from_help(help_output):
    # type: (str) -> list
    """The options of _RUN_OPTIONS_IF_SUPPORTED that *help_output* (the text
    of `jiecc --help`) mentions, in that order."""
    return [option for option in _RUN_OPTIONS_IF_SUPPORTED if option in help_output]


def probe_run_options(jiecc, root, timeout):
    # type: (str, str, int) -> list
    """run_options_from_help() of the installed jiecc; [] when --help fails."""
    code, output = _execute([jiecc, '--help'], root, timeout)
    if code is None:
        return []
    return run_options_from_help(output)


# The processes that are running, so that an interrupted run can kill them.
# After _stopping is set, no new process is started.
_live_lock = threading.Lock()
_live = set()
_stopping = threading.Event()


def _popen_options():
    # type: () -> dict
    if os.name == 'nt':
        return {}
    # A new session makes the process the leader of a new process group, so
    # the whole tree can be killed with os.killpg.
    return {'start_new_session': True}


def _windows_pid(proc):
    # type: (subprocess.Popen) -> int
    """Return the Windows process ID of proc (it differs from proc.pid under Cygwin)."""
    if sys.platform == 'cygwin':
        try:
            with open('/proc/{}/winpid'.format(proc.pid)) as f:
                return int(f.read().strip())
        except (IOError, OSError, ValueError):
            pass
    return proc.pid


def _kill_tree(proc):
    # type: (subprocess.Popen) -> None
    """Kill proc and all of its descendants."""
    if os.name == 'nt' or sys.platform == 'cygwin':
        # jiecc.exe starts a child that does the work; killing only proc would
        # leave the child running with the output pipe open.
        try:
            subprocess.call(['taskkill', '/T', '/F', '/PID', str(_windows_pid(proc))],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            # Without taskkill only proc itself can be killed; the drain in
            # _execute then reports whether a child still holds the output.
            print('warning: cannot run taskkill: {}'.format(e), file=sys.stderr)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def kill_live_processes():
    # type: () -> None
    """Stop starting new processes and kill the running ones (with their trees)."""
    with _live_lock:
        _stopping.set()
        procs = list(_live)
    for proc in procs:
        _kill_tree(proc)


def _execute(cmd, cwd, timeout):
    # type: (list, str, int) -> tuple
    """Run cmd and return (exit code, output), or (None, message) on a timeout or a start error."""
    with _live_lock:
        # Starting the process under the lock lets kill_live_processes see
        # every process that was started before _stopping was set.
        if _stopping.is_set():
            return None, 'not started (interrupted)'
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, **_popen_options())
        except OSError as e:
            return None, 'failed to start jiecc: {}'.format(e)
        _live.add(proc)
    try:
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            # The output pipe closes only when every process that holds it
            # has ended, so reading to the end confirms the tree is gone.
            try:
                proc.communicate(timeout=_DRAIN_TIMEOUT)
            except subprocess.TimeoutExpired:
                return None, ('timed out after {}s; a process still holds the output {}s after '
                              'the process tree was killed (a jiecc process may remain; '
                              'check the process list)'.format(timeout, _DRAIN_TIMEOUT))
            return None, 'timed out after {}s (the process tree was killed)'.format(timeout)
    finally:
        with _live_lock:
            _live.discard(proc)
    output = out.decode('utf-8', errors='replace') if out else ''
    return proc.returncode, output


def xml_path(outdir, item, target, keep):
    # type: (str, Item, str, bool) -> str
    """Return the XML output path of item for target.

    With keep (--output-dir), the path is outdir/<target>/<item name> with
    .iec replaced by .xml. Otherwise it is a flat name in the temporary
    directory.
    """
    if keep:
        stem = item.name[:-4] if item.name.endswith('.iec') else item.name
        return os.path.join(outdir, target, *(stem + '.xml').split('/'))
    stem = re.sub(r'[^A-Za-z0-9_.-]', '_', item.name)
    return os.path.join(outdir, '{}.{}.xml'.format(stem, target))


def _remove(path):
    # type: (str) -> None
    try:
        os.remove(path)
    except OSError:
        pass


def compile_item(jiecc, root, item, target, outdir, timeout, keep=False):
    # type: (str, str, Item, str, str, int, bool) -> tuple
    """Return (ok, detail lines, warning lines). The XML of a failed compile is removed."""
    out_path = xml_path(outdir, item, target, keep)
    if keep:
        # Several threads may create the same directory at the same time.
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [jiecc, item.path] + _common_args(root, item) + ['-o', _native_path(out_path),
                                                          '-t', target]
    code, output = _execute(cmd, root, timeout)
    if code is None:
        _remove(out_path)
        return False, [output], []
    lines = output.splitlines()
    error_lines = [line for line in lines if _RE_ERROR_TEXT.search(line)]
    warning_lines = [line for line in lines
                     if _RE_WARNING_TEXT.search(line) and line not in error_lines]
    if code != 0:
        _remove(out_path)
        return False, ['exit code {}'.format(code)] + (error_lines or lines[-20:]), warning_lines
    if error_lines:
        _remove(out_path)
        return False, ['exit code 0 but the output has "error: " line(s)'] + error_lines, warning_lines
    if keep and not os.path.isfile(out_path):
        return False, ['jiecc did not write {}'.format(out_path)], warning_lines
    return True, [], warning_lines


def judge_run_output(output):
    # type: (str) -> tuple
    """Judge the output of jiecc --run. Return (ok, detail lines)."""
    lines = output.splitlines()

    error_lines = [line for line in lines if _RE_ERROR_TEXT.search(line)]
    if error_lines:
        return False, ['the output has "error: " line(s)'] + error_lines
    fault_lines = [line for line in lines if _RE_FAULT_TEXT.search(line)]
    if fault_lines:
        return False, ['the output has "InterpreterFault" line(s)'] + fault_lines

    running = None
    ran = None
    passed = None
    skipped = 0
    for line in lines:
        m = _RE_RUNNING.match(line)
        if m:
            running = int(m.group(1))
            continue
        m = _RE_TESTS_RAN.match(line)
        if m:
            ran = int(m.group(1))
            continue
        m = _RE_PASSED.match(line)
        if m:
            passed = int(m.group(1))
            continue
        m = _RE_SKIPPED.match(line)
        if m:
            skipped = int(m.group(1))

    tail = lines[-20:]
    if running is None:
        return False, ['no "[========] Running N tests." line in the output'] + tail
    if ran is None:
        return False, ['no "[========] N tests ran." line in the output '
                       '(too few cycles? see --max-cycles)'] + tail
    if passed is None:
        return False, ['no "[ PASSED ] N tests." line in the output'] + tail
    failed_lines = [line for line in lines if _RE_FAILED_LINE.search(line)]
    if failed_lines:
        return False, ['the output has "[ FAILED ]" line(s)'] + failed_lines
    error_result_lines = [line for line in lines if _RE_ERROR_LINE.search(line)]
    if error_result_lines:
        return False, ['the output has "[  ERROR ]" line(s)'] + error_result_lines
    if ran != running:
        return False, ['{} tests ran, but {} were registered (too few cycles? see '
                       '--max-cycles)'.format(ran, running)]
    if passed + skipped != ran:
        return False, ['passed ({}) + skipped ({}) != ran ({})'.format(passed, skipped, ran)]
    return True, ['{} ran, {} passed, {} skipped'.format(ran, passed, skipped)]


def judge_run(code, output):
    # type: (int, str) -> tuple
    """Judge a finished jiecc --run by its exit code and its output.

    Return (ok, detail lines). The run fails when judge_run_output() fails or
    the exit code is not 0 (JiecUnit v7.0.0 exits with 1 on a failure).
    """
    ok, detail = judge_run_output(output)
    if code != 0:
        head = 'jiecc --run exited with code {}'.format(code)
        return False, [head] + (detail if not ok else output.splitlines()[-20:])
    return ok, detail


def run_item(jiecc, root, item, max_cycles, timeout, run_options=()):
    # type: (str, str, Item, int, int, tuple) -> tuple
    """Return (ok, detail lines) of judge_run(), or a failure on a timeout.
    *run_options* (probe_run_options()) are jiecc options added to every run."""
    cmd = ([jiecc, '--run', item.path] + _common_args(root, item)
           + ['--max-cycles', str(max_cycles)] + list(run_options))
    code, output = _execute(cmd, root, timeout)
    if code is None:
        return False, [output]
    return judge_run(code, output)


def _print_result(phase, name, target, ok, detail, warnings, elapsed=None):
    # type: (str, str, str, bool, list, list, float) -> None
    """Print the result line of one task, and the detail lines on a failure.

    *elapsed* (seconds, given for every run task) is shown as "[12.3 s]", so
    that a slow test file is noticed before it reaches --timeout.
    """
    status = 'OK' if ok else 'FAIL'
    head = detail[0] if (ok and detail) else ''
    seconds = '  [{:.1f} s]'.format(elapsed) if elapsed is not None else ''
    print('{:<4} {:<7} {:<8} {}{}{}'.format(
        status, phase, target, name, seconds, ('  (' + head + ')') if head else ''), flush=True)
    if not ok:
        for line in detail:
            print('       ' + line, flush=True)
    for line in warnings:
        print('       ' + line, flush=True)


def main(argv=None):
    # type: (list) -> int
    parser = argparse.ArgumentParser(
        description='Compile and run the JiecLib sources and tests with jiecc.')
    parser.add_argument('paths', nargs='*',
                        help='Files or directories to check (default: all source entry '
                             'files under src/ and all test files under test/).')
    parser.add_argument('--jiecc', default=None,
                        help='Path to the jiecc executable. Falls back to the JIECC '
                             'environment variable, then to jiecc on PATH.')
    parser.add_argument('--compile-only', action='store_true',
                        help='Only compile; do not run the tests.')
    parser.add_argument('--run-only', action='store_true',
                        help='Only run the tests; do not compile.')
    parser.add_argument('--jobs', '-j', type=int, default=os.cpu_count() or 1,
                        help='Number of parallel jiecc processes (default: CPU count).')
    parser.add_argument('--max-cycles', type=int, default=_DEFAULT_MAX_CYCLES,
                        help='Maximum scan cycles for jiecc --run, a safety cap for '
                             'a test that never halts (default: {}).'.format(
                                 _DEFAULT_MAX_CYCLES))
    parser.add_argument('--timeout', type=int, default=_DEFAULT_TIMEOUT,
                        help='Timeout in seconds for each jiecc invocation '
                             '(default: {}).'.format(_DEFAULT_TIMEOUT))
    parser.add_argument('--output-dir', default=None,
                        help='Keep the XML files as DIR/<target>/<path>.xml instead of '
                             'writing them to a temporary directory.')
    args = parser.parse_args(argv)

    if args.compile_only and args.run_only:
        print('error: --compile-only and --run-only are mutually exclusive.', file=sys.stderr)
        return 2
    if args.output_dir and args.run_only:
        print('error: --output-dir cannot be used with --run-only (nothing is compiled).',
              file=sys.stderr)
        return 2
    if args.jobs < 1:
        print('error: --jobs must be 1 or more.', file=sys.stderr)
        return 2
    if args.max_cycles < 1 or args.timeout < 1:
        print('error: --max-cycles and --timeout must be 1 or more.', file=sys.stderr)
        return 2

    root = _repo_root()
    items, errors = _select(root, _discover(root), args.paths)
    for line in errors:
        print('error: ' + line, file=sys.stderr)

    keep = bool(args.output_dir)
    if keep:
        outside = [item.name for item in items if not item.in_repo]
        if outside:
            for name in outside:
                print('error: {}: --output-dir needs a file in the repository'.format(name),
                      file=sys.stderr)
            return 2

    jiecc = _resolve_jiecc(args.jiecc)
    run_options = [] if args.compile_only else probe_run_options(jiecc, root, args.timeout)

    tasks = []
    if not args.run_only:
        for item in items:
            for target in item.targets:
                tasks.append(('compile', item, target))
    skipped_runs = []
    if not args.compile_only:
        selected_tests = set(os.path.normcase(os.path.abspath(os.path.join(root, item.name)))
                             for item in items if item.kind == 'test')
        for item in items:
            if item.kind != 'test':
                continue
            # An aggregate test file runs the same tests as the files it
            # includes; when all of them run too, running it again under
            # jier only doubles the time. It is still compiled.
            if item.included_tests and all(p in selected_tests for p in item.included_tests):
                skipped_runs.append(item)
                continue
            tasks.append(('run', item, '-'))
    for item in skipped_runs:
        print('SKIP run     -        {}  (aggregate; its {} included test files run one by one)'
              .format(item.name, len(item.included_tests)))

    if keep:
        outdir = os.path.abspath(args.output_dir)
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = tempfile.mkdtemp(prefix='jieclib_run_tests_')
    failures = []
    counts = {'compile': [0, 0], 'run': [0, 0]}

    def work(task):
        phase, item, target = task
        elapsed = None
        if phase == 'compile':
            ok, detail, warnings = compile_item(jiecc, root, item, target, outdir,
                                                args.timeout, keep)
        else:
            start = time.time()
            ok, detail = run_item(jiecc, root, item, args.max_cycles, args.timeout,
                                  run_options)
            elapsed = time.time() - start
            warnings = []
        return task, ok, detail, warnings, elapsed

    _stopping.clear()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = []
            try:
                for t in tasks:
                    futures.append(pool.submit(work, t))
                for future in concurrent.futures.as_completed(futures):
                    (phase, item, target), ok, detail, warnings, elapsed = future.result()
                    _print_result(phase, item.name, target, ok, detail, warnings, elapsed)
                    counts[phase][0 if ok else 1] += 1
                    if not ok:
                        failures.append('{} {} {}'.format(phase, target, item.name))
            except BaseException:
                # On Ctrl+C (or an unexpected error), do not leave jiecc
                # processes behind, and do not wait for the queued tasks.
                for future in futures:
                    future.cancel()
                kill_live_processes()
                raise
    finally:
        if not keep:
            shutil.rmtree(outdir, ignore_errors=True)

    print('')
    print('Summary:')
    if not args.run_only:
        print('  compile: {} passed, {} failed'.format(*counts['compile']))
    if not args.compile_only:
        line = '  run:     {} passed, {} failed'.format(*counts['run'])
        if skipped_runs:
            line += ', {} aggregate skipped'.format(len(skipped_runs))
        print(line)
    if errors:
        print('  path errors: {}'.format(len(errors)))
    for line in sorted(failures):
        print('  FAIL ' + line)

    if not tasks:
        print('error: nothing to check.', file=sys.stderr)
        return 1
    if failures or errors:
        print('One or more checks failed.')
        return 1
    print('All checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
