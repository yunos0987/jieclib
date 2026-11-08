#!/usr/bin/env python
# coding: utf-8
"""Check that a pull request body records the L3 / L4 test results.

L3 (a run on the Sysmac Studio simulator) and L4 (a run on KV Studio) cannot
be checked by CI, so .github/pull_request_template.md has a section for each,
and this script checks that the required sections are filled in:

  - L3 is required when the pull request changes a file under src/.
  - L4 is required when it changes a .iec file under src/, test/ or samples/
    that declares the keyence target, or a file that such a file includes
    (directly or through other files: sys.iec, array/array.iec, ...), since
    the change reaches the KV Studio build of that file. A file without a
    "$ jiecc" header that no keyence file includes (a deleted file, ...)
    uses the targets declared by the other files of the same module:
    src/<module>/ and test/<module>/, or for the files directly under src/
    and test/, the module "sys".

A filled-in section has "- 結果:" set to 合格, 不合格 or 未実施. 合格 and 不合格
also need "- 開発環境と版:" and "- 実行したテストファイル:"; 未実施 needs
"- 未実施の理由:". HTML comments in the body are ignored. Only the format is
checked; reviewers check the content.

Usage (CI passes the body in the PR_BODY environment variable):
  python scripts/check_pr_body.py --base <commit>
  python scripts/check_pr_body.py --base <commit> --body-file body.md
"""
import argparse
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from run_tests import _header_targets  # noqa: E402

_RESULTS = ('合格', '不合格', '未実施')
_FIELD_RESULT = '結果'
_FIELD_ENV = '開発環境と版'
_FIELD_FILES = '実行したテストファイル'
_FIELD_REASON = '未実施の理由'
_SECTIONS = {
    'L3': 'Sysmac Studio のシミュレータでの実行',
    'L4': 'KV Studio での実行',
}
_TOPS = ('src', 'test', 'samples')

_RE_COMMENT = re.compile(r'<!--.*?-->', re.S)
_RE_HEADING = re.compile(r'^##[ \t]+(.*?)[ \t]*$', re.M)
# The level is the first word of a heading: "## L3 ...", "## L3: ...", "## L3（...）".
_RE_LEVEL = re.compile(r'^(L[34])(?![0-9A-Za-z_])')
# The result is the first word of the value: "合格", "合格（全件）", "**合格**".
_RE_RESULT = re.compile(r'^(不合格|合格|未実施)(?=$|[\s(（、。,:：])')
# {#include <path>} (searched in the repository root, src/ and vendor/jiecunit)
# or {#include "path"} (searched next to the including file first).
_RE_INCLUDE = re.compile(r'\{#include[ \t]+([<"])([^>"]+)[>"]')
_RE_FIELD = re.compile(r'^[-*][ \t]+([^:：\n]+?)[ \t]*[:：][ \t]*(.*)$')


def _read_text(path):
    # type: (str) -> str
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def parse_sections(body):
    # type: (str) -> dict
    """Return {level: {field: value}} for the "## L3 ..." and "## L4 ..." sections.

    A field value is the text after the colon plus the indented lines that
    follow it (for a list of test files).
    """
    body = _RE_COMMENT.sub('', body.replace('\r\n', '\n'))
    headings = list(_RE_HEADING.finditer(body))
    sections = {}
    for index, m in enumerate(headings):
        lm = _RE_LEVEL.match(m.group(1))
        if not lm:
            continue
        level = lm.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        fields = {}
        current = None
        for line in body[m.end():end].splitlines():
            fm = _RE_FIELD.match(line)
            if fm:
                current = fm.group(1).strip()
                fields[current] = fm.group(2).strip()
            elif current and line[:1] in (' ', '\t') and line.strip():
                fields[current] = (fields[current] + '\n' + line.strip()).strip()
            elif line.strip():
                current = None
        sections[level] = fields
    return sections


def check_section(level, fields):
    # type: (str, dict) -> list
    """Return the errors of one section (fields is None when the section is missing)."""
    title = '{} ({})'.format(level, _SECTIONS[level])
    if fields is None:
        return ['the "## {} {}" section is missing; use .github/pull_request_template.md'.format(
            level, _SECTIONS[level])]
    result = fields.get(_FIELD_RESULT, '')
    rm = _RE_RESULT.match(re.sub(r'[*_`]', '', result).strip())
    if rm:
        result = rm.group(1)
    else:
        return ['{}: "- {}:" must be one of {} (found {!r})'.format(
            title, _FIELD_RESULT, ' / '.join(_RESULTS), result)]
    errors = []
    needed = (_FIELD_REASON,) if result == '未実施' else (_FIELD_ENV, _FIELD_FILES)
    for name in needed:
        if not fields.get(name, ''):
            errors.append('{}: "- {}:" is empty (required when the result is {})'.format(
                title, name, result))
    return errors


def _module_of(path):
    # type: (str) -> str
    """Return the module of a repository-relative path, or None."""
    parts = path.split('/')
    if parts[0] not in _TOPS or len(parts) < 2:
        return None
    if len(parts) == 2:
        return 'sys' if parts[0] in ('src', 'test') else None
    return parts[1]


def _module_targets(root, module):
    # type: (str, str) -> set
    """Return the union of the targets declared by the files of a module."""
    targets = set()
    for top in ('src', 'test'):
        base = os.path.join(root, top)
        if module == 'sys':
            names = [os.path.join(base, n) for n in sorted(os.listdir(base))] \
                if os.path.isdir(base) else []
            paths = [p for p in names if p.endswith('.iec') and os.path.isfile(p)]
        else:
            paths = []
            for dirpath, dirnames, filenames in os.walk(os.path.join(base, module)):
                paths.extend(os.path.join(dirpath, n) for n in filenames if n.endswith('.iec'))
        for p in paths:
            targets.update(_header_targets(_read_text(p)))
    return targets


def declared_targets(root, path):
    # type: (str, str) -> set
    """Return the targets that apply to a changed file (see the module docstring)."""
    full = os.path.join(root, path)
    if os.path.isfile(full):
        own = _header_targets(_read_text(full))
        if own:
            return set(own)
    module = _module_of(path)
    return _module_targets(root, module) if module else set()


def _resolve_include(root, including, kind, name):
    # type: (str, str, str, str) -> str
    """Return the repository-relative path of an included file, or ''."""
    bases = []
    if kind == '"':
        bases.append(os.path.dirname(including))
    bases.extend(['', 'src', 'vendor/jiecunit'])
    for base in bases:
        rel = os.path.normpath(os.path.join(base, name)).replace(os.sep, '/')
        if os.path.isfile(os.path.join(root, rel)):
            return rel
    return ''


def keyence_files(root):
    # type: (str) -> set
    """Return the .iec files that are part of a keyence build.

    These are the files that declare keyence on a "$ jiecc" line, and every
    file that they include, directly or through other files.
    """
    found = set()
    pending = []
    for top in _TOPS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, top)):
            for name in filenames:
                if name.endswith('.iec'):
                    rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, '/')
                    if 'keyence' in _header_targets(_read_text(os.path.join(root, rel))):
                        pending.append(rel)
    while pending:
        rel = pending.pop()
        if rel in found:
            continue
        found.add(rel)
        for kind, name in _RE_INCLUDE.findall(_read_text(os.path.join(root, rel))):
            target = _resolve_include(root, rel, kind, name)
            if target and target not in found:
                pending.append(target)
    return found


def required_levels(root, changed):
    # type: (str, list) -> list
    levels = []
    if any(p.startswith('src/') for p in changed):
        levels.append('L3')
    keyence = keyence_files(root)
    for p in changed:
        if not (p.endswith('.iec') and p.split('/')[0] in _TOPS):
            continue
        if p in keyence or 'keyence' in declared_targets(root, p):
            levels.append('L4')
            break
    return levels


def check(body, changed, root):
    # type: (str, list, str) -> tuple
    """Return (required levels, errors)."""
    levels = required_levels(root, changed)
    sections = parse_sections(body)
    errors = []
    for level in levels:
        errors.extend(check_section(level, sections.get(level)))
    return levels, errors


def _changed_files(root, base):
    # type: (str, str) -> list
    # -z keeps non-ASCII paths unquoted (core.quotePath would quote them), and
    # --no-renames lists both the old and the new path of a moved file.
    out = subprocess.check_output(['git', 'diff', '--name-only', '-z', '--no-renames', base,
                                   'HEAD'], cwd=root)
    return [p for p in out.decode('utf-8').split('\0') if p]


def main(argv=None):
    # type: (list) -> int
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--base', required=True,
                        help='commit to compare with (the merge base of the pull request)')
    parser.add_argument('--body-file', help='read the body from this file instead of PR_BODY')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    root = os.path.dirname(_HERE)
    body = _read_text(args.body_file) if args.body_file else os.environ.get('PR_BODY', '')
    try:
        changed = _changed_files(root, args.base)
    except (OSError, subprocess.CalledProcessError) as e:
        print('error: cannot list the changed files: {}'.format(e))
        return 2
    levels, errors = check(body, changed, root)
    if not levels:
        print('No L3 / L4 record is required ({} changed files).'.format(len(changed)))
        return 0
    for message in errors:
        print('error: pr-body: {}'.format(message))
    if errors:
        print('Fill in the {} section(s) of the pull request body.'.format(' and '.join(levels)))
        return 1
    print('The pull request body records {}.'.format(' and '.join(levels)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
