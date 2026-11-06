#!/usr/bin/env python
# coding: utf-8
"""Make the table of the targets that each library declares, for README.md.

A library (an "object") is a directory under src/: src/<module>/ and the
tests under test/<module>/ belong to it. The files directly under src/ and
test/ (sys.iec, test_sys.iec, ...) are the object "sys". The targets of
an object are the targets on the "$ jiecc" lines of the header comments of
its entry files under src/; when no file under src/ has a header (the
templates of container, sys.iec, ...), the headers of its tests declare
them. The files and targets are those that run_tests.py compiles (a test
without a header is compiled for omron). The sources and the tests of an
object must declare the same targets (lint rule target-consistency).

README.md has the table between the lines
  <!-- target-table:begin -->
  <!-- target-table:end -->

Usage:
  python scripts/target_table.py           # print the table
  python scripts/target_table.py --check   # fail if README.md differs
  python scripts/target_table.py --update  # rewrite the table in README.md
"""
import argparse
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import run_tests  # noqa: E402

BEGIN = '<!-- target-table:begin -->'
END = '<!-- target-table:end -->'
SYS = 'sys'


def object_of(rel):
    # type: (str) -> str
    """Return the object of a repository-relative path under src/ or test/, or ''."""
    parts = rel.split('/')
    if parts[0] not in ('src', 'test') or len(parts) < 2:
        return ''
    return SYS if len(parts) == 2 else parts[1]


def declarations(root):
    # type: (str) -> collections.OrderedDict
    """Return {object: (targets of src/, targets of test/)} (sets), sorted by object.

    The files and their targets are those that run_tests.py compiles: the
    entry files of src/ (with a "$ jiecc" header) and the test files of
    test/ (with DEFINE_CONFIGURATION; a test without a header is compiled
    for omron, so it declares omron).
    """
    found = {}
    for item in run_tests._discover(root):
        obj = object_of(item.name)
        if not obj:
            continue
        src_targets, test_targets = found.setdefault(obj, (set(), set()))
        (src_targets if item.name.startswith('src/') else test_targets).update(item.targets)
    return collections.OrderedDict(sorted(found.items()))


def declared(src_targets, test_targets):
    # type: (set, set) -> set
    return src_targets if src_targets else test_targets


def mismatches(root):
    # type: (str) -> list
    """Return [(object, src targets, test targets)] whose declarations differ."""
    result = []
    for obj, (src_targets, test_targets) in declarations(root).items():
        if src_targets and test_targets and src_targets != test_targets:
            result.append((obj, sorted(src_targets), sorted(test_targets)))
    return result


def render(root):
    # type: (str) -> str
    lines = ['| ライブラリ | 宣言したターゲット |', '|---|---|']
    for obj, (src_targets, test_targets) in declarations(root).items():
        link = '[sys](./src)（`src/` 直下の `sys.iec` など）' if obj == SYS else \
            '[{0}](./src/{0})'.format(obj)
        lines.append('| {} | {} |'.format(link, ', '.join(sorted(declared(src_targets, test_targets)))))
    return '\n'.join(lines) + '\n'


def replace_table(text, table):
    # type: (str, str) -> str
    """Return text with the table between the markers replaced. Raise ValueError without markers."""
    begin = text.find(BEGIN)
    end = text.find(END)
    if begin < 0 or end < begin:
        raise ValueError('README.md has no {} ... {} lines'.format(BEGIN, END))
    return text[:begin + len(BEGIN)] + '\n' + table + text[end:]


def main(argv=None, root=None):
    # type: (list, str) -> int
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='fail if README.md differs')
    mode.add_argument('--update', action='store_true', help='rewrite the table in README.md')
    args = parser.parse_args(argv)
    root = root or run_tests._repo_root()
    table = render(root)
    if not (args.check or args.update):
        sys.stdout.write(table)
        return 0
    readme = os.path.join(root, 'README.md')
    with open(readme, encoding='utf-8') as f:
        text = f.read()
    try:
        new = replace_table(text, table)
    except ValueError as e:
        print('error: {}'.format(e))
        return 1
    if args.update:
        with open(readme, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new)
        print('Updated the target table in README.md.')
        return 0
    if new != text:
        print('error: the target table in README.md does not match the headers; run '
              '"python scripts/target_table.py --update". Expected:')
        sys.stdout.write(table)
        return 1
    print('The target table in README.md matches the headers.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
