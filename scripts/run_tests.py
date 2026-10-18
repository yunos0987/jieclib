#!/usr/bin/env python
# coding: utf-8
"""Compile and run the JiecLib sources and tests with jiecc.

Compile phase:
  - Every source entry file under src/ (a file whose header comment has a
    "$ jiecc" command line) and every test file under test/ that contains
    DEFINE_CONFIGURATION is compiled for each target named by "-t <target>"
    on the "$ jiecc" lines of its header comment (OMRON when none is named).
  - Include paths are the repository root, src and vendor/jiecunit.
    Test files are compiled with -D_TEST_.
  - The XML output goes to a temporary directory, never into the repository.
  - A compile fails when jiecc exits with a nonzero code or prints an
    "error: " line. Warnings are printed but do not fail the check.

Run phase:
  - Every test file is interpreted with the jier interpreter
    (`jiecc --run ... -D_TEST_ --max-cycles N`).
  - jiecc's exit code does not reflect test failures in --run mode, so the
    result is judged from the JiecUnit summary lines on stdout. A run passes
    only when the summary is printed, no "[ FAILED ]" line is printed, and no
    "error: " or "InterpreterFault" line is printed.

The jiecc executable is looked up in this order: --jiecc PATH, the JIECC
environment variable, then jiecc on PATH.

Usage:
  python scripts/run_tests.py
  python scripts/run_tests.py --jiecc /path/to/jiecc.exe
  python scripts/run_tests.py --compile-only
  python scripts/run_tests.py --run-only test/math/test_floor.iec
  python scripts/run_tests.py src/array test/array --jobs 4
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile

_DEFAULT_TARGET = 'omron'
_DEFAULT_MAX_CYCLES = 100000
_DEFAULT_TIMEOUT = 1800

_RE_TESTS_RAN = re.compile(r'^\[========\] (\d+) tests ran\.')
_RE_PASSED = re.compile(r'^\[ PASSED \] (\d+) tests\.')
_RE_SKIPPED = re.compile(r'^\[ SKIPPED\] (\d+) tests\.')
_RE_FAILED_LINE = re.compile(r'\[ FAILED \]')
_RE_ERROR_LINE = re.compile(r'\[  ERROR \]')
# jiecc can print an "error: " line while still exiting 0, so the output text
# is scanned regardless of the process exit code.
_RE_ERROR_TEXT = re.compile(r'(?m)^\S.*: error: | error: ')
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
    """A file to check: its display name, path, kind ('src' or 'test') and targets."""

    def __init__(self, name, path, kind, targets):
        # type: (str, str, str, list) -> None
        self.name = name
        self.path = path
        self.kind = kind
        self.targets = targets


def _make_item(root, path, text):
    # type: (str, str, str) -> Item
    rel = os.path.relpath(path, root)
    if rel.startswith('..'):
        name = path
        arg = _native_path(path)
    else:
        name = rel.replace(os.sep, '/')
        arg = name
    kind = 'test' if 'DEFINE_CONFIGURATION' in text else 'src'
    targets = _header_targets(text) or [_DEFAULT_TARGET]
    return Item(name, arg, kind, targets)


def _discover(root):
    # type: (str) -> list
    items = []
    for top, kind in (('src', 'src'), ('test', 'test')):
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
        path = os.path.normcase(os.path.abspath(raw))
        if os.path.isdir(path):
            prefix = path.rstrip(os.sep) + os.sep
            matched = [item for key, item in sorted(by_path.items()) if key.startswith(prefix)]
            if not matched:
                errors.append('{}: no source entry file or test file in this directory'.format(raw))
            for item in matched:
                if item not in selected:
                    selected.append(item)
        elif os.path.isfile(path):
            item = by_path.get(path)
            if item is None:
                item = _make_item(root, os.path.abspath(raw), _read_text(raw))
            if item not in selected:
                selected.append(item)
        else:
            errors.append('{}: no such file or directory'.format(raw))
    return selected, errors


def _common_args(root, item):
    # type: (str, Item) -> list
    args = ['-I.', '-I./src', '-I./vendor/jiecunit']
    if item.kind == 'test':
        args.append('-D_TEST_')
    return args


def _execute(cmd, cwd, timeout):
    # type: (list, str, int) -> tuple
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, 'timed out after {}s'.format(timeout)
    except OSError as e:
        return None, 'failed to start jiecc: {}'.format(e)
    output = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
    return proc.returncode, output


def compile_item(jiecc, root, item, target, outdir, timeout):
    # type: (str, str, Item, str, str, int) -> tuple
    """Return (ok, detail lines, warning lines)."""
    stem = re.sub(r'[^A-Za-z0-9_.-]', '_', item.name)
    out_xml = _native_path(os.path.join(outdir, '{}.{}.xml'.format(stem, target)))
    cmd = [jiecc, item.path] + _common_args(root, item) + ['-o', out_xml, '-t', target]
    code, output = _execute(cmd, root, timeout)
    if code is None:
        return False, [output], []
    lines = output.splitlines()
    error_lines = [line for line in lines if _RE_ERROR_TEXT.search(line)]
    warning_lines = [line for line in lines
                     if _RE_WARNING_TEXT.search(line) and line not in error_lines]
    if code != 0:
        return False, ['exit code {}'.format(code)] + (error_lines or lines[-20:]), warning_lines
    if error_lines:
        return False, ['exit code 0 but the output has "error: " line(s)'] + error_lines, warning_lines
    return True, [], warning_lines


def run_item(jiecc, root, item, max_cycles, timeout):
    # type: (str, str, Item, int, int) -> tuple
    """Return (ok, detail lines). The exit code of jiecc --run is not used."""
    cmd = ([jiecc, '--run', item.path] + _common_args(root, item)
           + ['--max-cycles', str(max_cycles)])
    code, output = _execute(cmd, root, timeout)
    if code is None:
        return False, [output]
    lines = output.splitlines()

    error_lines = [line for line in lines if _RE_ERROR_TEXT.search(line)]
    if error_lines:
        return False, ['the output has "error: " line(s)'] + error_lines
    fault_lines = [line for line in lines if _RE_FAULT_TEXT.search(line)]
    if fault_lines:
        return False, ['the output has "InterpreterFault" line(s)'] + fault_lines

    ran = None
    passed = None
    skipped = 0
    for line in lines:
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
    if ran is None:
        return False, ['no "[========] N tests ran." line in the output'] + tail
    if passed is None:
        return False, ['no "[ PASSED ] N tests." line in the output'] + tail
    failed_lines = [line for line in lines if _RE_FAILED_LINE.search(line)]
    if failed_lines:
        return False, ['the output has "[ FAILED ]" line(s)'] + failed_lines
    error_result_lines = [line for line in lines if _RE_ERROR_LINE.search(line)]
    if error_result_lines:
        return False, ['the output has "[  ERROR ]" line(s)'] + error_result_lines
    if passed + skipped != ran:
        return False, ['passed ({}) + skipped ({}) != ran ({})'.format(passed, skipped, ran)]
    return True, ['{} ran, {} passed, {} skipped'.format(ran, passed, skipped)]


def _print_result(phase, name, target, ok, detail, warnings):
    # type: (str, str, str, bool, list, list) -> None
    status = 'OK' if ok else 'FAIL'
    head = detail[0] if (ok and detail) else ''
    print('{:<4} {:<7} {:<8} {}{}'.format(
        status, phase, target, name, ('  (' + head + ')') if head else ''), flush=True)
    if not ok:
        for line in detail:
            print('       ' + line, flush=True)
    for line in warnings:
        print('       ' + line, flush=True)


def main():
    # type: () -> int
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
                        help='Maximum scan cycles for jiecc --run '
                             '(default: {}).'.format(_DEFAULT_MAX_CYCLES))
    parser.add_argument('--timeout', type=int, default=_DEFAULT_TIMEOUT,
                        help='Timeout in seconds for each jiecc invocation '
                             '(default: {}).'.format(_DEFAULT_TIMEOUT))
    args = parser.parse_args()

    if args.compile_only and args.run_only:
        print('error: --compile-only and --run-only are mutually exclusive.', file=sys.stderr)
        return 2
    if args.jobs < 1:
        print('error: --jobs must be 1 or more.', file=sys.stderr)
        return 2

    jiecc = _resolve_jiecc(args.jiecc)
    root = _repo_root()
    items, errors = _select(root, _discover(root), args.paths)
    for line in errors:
        print('error: ' + line, file=sys.stderr)

    tasks = []
    if not args.run_only:
        for item in items:
            for target in item.targets:
                tasks.append(('compile', item, target))
    if not args.compile_only:
        for item in items:
            if item.kind == 'test':
                tasks.append(('run', item, '-'))

    outdir = tempfile.mkdtemp(prefix='jieclib_run_tests_')
    failures = []
    counts = {'compile': [0, 0], 'run': [0, 0]}

    def work(task):
        phase, item, target = task
        if phase == 'compile':
            ok, detail, warnings = compile_item(jiecc, root, item, target, outdir, args.timeout)
        else:
            ok, detail = run_item(jiecc, root, item, args.max_cycles, args.timeout)
            warnings = []
        return task, ok, detail, warnings

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for future in concurrent.futures.as_completed([pool.submit(work, t) for t in tasks]):
                (phase, item, target), ok, detail, warnings = future.result()
                _print_result(phase, item.name, target, ok, detail, warnings)
                counts[phase][0 if ok else 1] += 1
                if not ok:
                    failures.append('{} {} {}'.format(phase, target, item.name))
    finally:
        shutil.rmtree(outdir, ignore_errors=True)

    print('')
    print('Summary:')
    if not args.run_only:
        print('  compile: {} passed, {} failed'.format(*counts['compile']))
    if not args.compile_only:
        print('  run:     {} passed, {} failed'.format(*counts['run']))
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
