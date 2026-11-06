#!/usr/bin/env python
# coding: utf-8
"""Check the JiecLib sources against the coding rules that can be checked mechanically.

The rules come from CONTRIBUTING.md and AGENTS.md. This script reads the .iec
sources directly; it does not need jiecc.

Rules (rule id, severity):
  keyword-case   error    Keywords, true/false, elementary type names and
                          standard function names are written in lowercase.
                          Names defined with {#define} are not checked.
  doc-apostrophe error    Apostrophes in a doc pragma come in pairs (an
                          unpaired one makes jiepp print warning PP29).
  doc-missing    error    Every POU under src/ is directly preceded by a doc
                          pragma.
  doc-style      error    Doc pragmas are written as (*{doc ...}*).
  doc-language   warning  Doc pragmas and comments use ASCII only (English).
  no-continue    error    continue is not used.
  no-c-comment   error    /* */ comments are not used.
  test-fact      warning  Every TEST_S / TEST_M has a "// Fact:" comment.
  parse          error    The file can be split into code, comments, strings
                          and pragmas (e.g. no unterminated comment).

With --xml-dir DIR, the rules of scripts/lint_xml.py also check the XML
that `python scripts/run_tests.py --compile-only --output-dir DIR` wrote
(names and types after preprocessing, including the names made by the
templates): xml-missing, pou-name-length, reserved-name, omron-p-prefix,
varlen-array-inout, no-struct-return, no-alias-type (errors) and
keyence-names (a warning).

Warnings are managed with a baseline (scripts/lint_baseline.json): the list of
warnings that existed when the rule was introduced. A warning that is not in
the list fails the check. Entries do not contain line numbers, so moving code
does not change them.

Output: one finding per line, "<path>:<line>: <severity>: <rule>: <message>".
Exit code: 0 when there is no error and no new warning, 1 otherwise, 2 for a
usage or input error.

Usage:
  python scripts/lint.py                    # check src/, test/ (and samples/)
  python scripts/lint.py src/math           # check some files or directories
  python scripts/lint.py --update-baseline  # drop fixed warnings from the baseline
  python scripts/lint.py --reset-baseline   # rewrite the baseline from scratch
  python scripts/lint.py --check-baseline-against <commit>
  python scripts/run_tests.py --compile-only --output-dir out
  python scripts/lint.py --xml-dir out      # also check the compiled XML
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lint_xml  # noqa: E402
import run_tests  # noqa: E402

_DEFAULT_DIRS = ('src', 'test', 'samples')
# Directories whose {#define} names are collected even when they are not linted.
_MACRO_DIRS = ('src', 'test', 'samples', os.path.join('vendor', 'jiecunit'))
_BASELINE_REL = 'scripts/lint_baseline.json'

ERROR = 'error'
WARNING = 'warning'

RULES = collections.OrderedDict([
    ('keyword-case', ERROR),
    ('doc-apostrophe', ERROR),
    ('doc-missing', ERROR),
    ('doc-style', ERROR),
    ('doc-language', WARNING),
    ('no-continue', ERROR),
    ('no-c-comment', ERROR),
    ('test-fact', WARNING),
    ('parse', ERROR),
])
SOURCE_RULES = tuple(RULES)
SOURCE_WARNING_RULES = tuple(r for r, s in RULES.items() if s == WARNING)
RULES.update(lint_xml.RULES)
XML_WARNING_RULES = tuple(r for r, s in lint_xml.RULES if s == WARNING)
WARNING_RULES = tuple(r for r, s in RULES.items() if s == WARNING)

_KEYWORDS = frozenset('''
    and or xor not mod
    if then elsif else end_if case of end_case
    for to by do end_for while end_while repeat until end_repeat
    exit return continue
    function end_function function_block end_function_block program end_program
    var var_input var_output var_in_out var_temp var_external var_global
    var_access var_config end_var constant retain non_retain at end
    type end_type struct end_struct array
    configuration end_configuration resource end_resource on task with
    ref_to ref null this super
    method end_method interface end_interface class end_class
    extends implements abstract final public private protected internal
    step end_step initial_step transition end_transition from action end_action
    namespace end_namespace using
    true false
'''.split())

_TYPES = (
    'bool sint int dint lint usint uint udint ulint real lreal '
    'byte word dword lword string wstring char wchar '
    'time ltime date ldate time_of_day ltime_of_day tod ltod '
    'date_and_time ldate_and_time dt ldt').split()

_STD_FUNCTIONS = frozenset('''
    abs sqrt ln log exp expt sin cos tan asin acos atan atan2
    trunc shl shr rol ror sel max min limit mux move
    len left right mid concat insert delete replace find
'''.split())

_LOWERCASE_WORDS = _KEYWORDS | frozenset(_TYPES) | _STD_FUNCTIONS
# Type conversion functions such as lreal_to_dint.
_RE_CONVERSION = re.compile(r'^(?:%s)_to_(?:%s)$' % ('|'.join(_TYPES), '|'.join(_TYPES)))

_RE_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_RE_POU_HEADER = re.compile(r'(?im)^[ \t]*(function_block|function|program)[ \t]+([A-Za-z_]\w*)')
_RE_TEST_BEGIN = re.compile(r'\b(TEST_[SM])[ \t]*\([ \t]*([A-Za-z_]\w*)[ \t]*\)')
_RE_TEST_END = re.compile(r'\bEND_TEST_[SM]\b')
_RE_FACT = re.compile(r'^\s*Fact:')
_RE_NON_ASCII = re.compile(r'[^\x00-\x7f]')
_RE_DEFINE = re.compile(r'\{#define[ \t]+([A-Za-z_]\w*)(\([^)\n]*\))?')


def _repo_root():
    # type: () -> str
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Finding(object):
    """One rule violation. key identifies a warning in the baseline."""

    def __init__(self, rule, path, line, message, key=None):
        self.rule = rule
        self.severity = RULES[rule]
        self.path = path
        self.line = line
        self.message = message
        self.key = key

    def format(self):
        # type: () -> str
        return '{}:{}: {}: {}: {}'.format(self.path, self.line, self.severity, self.rule,
                                          self.message)


class Doc(object):
    """A doc pragma: style is '(*{doc', '(*{doc:', '{doc' or '{doc:'."""

    def __init__(self, start, end, style, body, body_start):
        self.start = start
        self.end = end
        self.style = style
        self.body = body
        self.body_start = body_start


class Comment(object):
    """A comment: kind is 'line' (// ...) or 'block' ((* ... *))."""

    def __init__(self, start, end, kind, text):
        self.start = start
        self.end = end
        self.kind = kind
        self.text = text


class Scan(object):
    """A source split into code, comments, strings and pragmas.

    code has the same length as the text; everything that is not code
    (comments, strings, pragmas, macro headers) is replaced with spaces, and
    newlines are kept so that offsets and line numbers stay the same. The body
    of a {#define} is code, because templates and macros contain ST code.
    """

    def __init__(self, text):
        self.text = text
        self.docs = []
        self.comments = []
        self.macros = set()
        self.errors = []  # (offset, message)
        self._mask = list(text)
        self._scan(0, False)
        self.code = ''.join(self._mask)

    def _blank(self, start, end):
        for i in range(start, min(end, len(self.text))):
            if self._mask[i] != '\n':
                self._mask[i] = ' '

    def _opener(self, i, in_define):
        # type: (int, bool) -> int
        """Return the length of a pragma opener at i: '{', or '${' in a {#define} body."""
        if self.text.startswith('{', i):
            return 1
        if in_define and self.text.startswith('${', i):
            return 2
        return 0

    def _is_doc(self, i):
        # type: (int) -> bool
        """Return whether a doc pragma name starts at i (just after the opener)."""
        if not self.text.startswith('doc', i):
            return False
        nxt = self.text[i + 3:i + 4]
        return nxt == '' or nxt in ':}$' or nxt.isspace()

    def _pragma_close(self, i, opener):
        # type: (int, int) -> tuple
        """Return (start, end) of the closer of the pragma opened at i.

        A pragma opened with '{' ends at the first '}' that is not escaped with
        '$'. A pragma escaped in a {#define} body ('${') ends at '$}'.
        """
        text = self.text
        n = len(text)
        j = i + opener
        while j < n:
            c = text[j]
            if c == '$':
                if opener == 2 and text.startswith('$}', j):
                    return j, j + 2
                j += 2
                continue
            if c == '}' and opener == 1:
                return j, j + 1
            j += 1
        self.errors.append((i, 'unterminated pragma'))
        return n, n

    def _read_doc(self, start, i, opener, wrapped):
        # type: (int, int, int, bool) -> int
        """Record the doc pragma opened at i (its comment starts at start). Return its end."""
        text = self.text
        name = i + opener
        colon = text.startswith('doc:', name)
        body_start = name + (4 if colon else 3)
        close, after = self._pragma_close(i, opener)
        end = after
        if wrapped:
            found = text.find('*)', after)
            if found < 0:
                self.errors.append((start, 'unterminated comment'))
                end = len(text)
            else:
                end = found + 2
        style = ('(*' if wrapped else '') + ('{doc:' if colon else '{doc')
        self.docs.append(Doc(start, end, style, text[body_start:close], body_start))
        self._blank(start, end)
        return end

    def _scan(self, i, in_define):
        # type: (int, bool) -> int
        """Scan from i. In a {#define} body, stop at its closing '}' and return it."""
        text = self.text
        n = len(text)
        while i < n:
            c = text[i]
            if text.startswith('(*', i):
                k = i + 2
                while k < n and text[k] in ' \t':
                    k += 1
                opener = self._opener(k, in_define)
                if opener and self._is_doc(k + opener):
                    i = self._read_doc(i, k, opener, True)
                    continue
                end = text.find('*)', i + 2)
                if end < 0:
                    self.errors.append((i, 'unterminated comment'))
                    self.comments.append(Comment(i, n, 'block', text[i + 2:]))
                    end = n
                else:
                    self.comments.append(Comment(i, end + 2, 'block', text[i + 2:end]))
                    end += 2
                self._blank(i, end)
                i = end
                continue
            if text.startswith('//', i):
                end = text.find('\n', i)
                if end < 0:
                    end = n
                self.comments.append(Comment(i, end, 'line', text[i + 2:end]))
                self._blank(i, end)
                i = end
                continue
            if c in '\'"':
                j = i + 1
                while j < n and text[j] != c:
                    j += 2 if text[j] == '$' else 1
                if j >= n:
                    self.errors.append((i, 'unterminated string literal'))
                end = min(j + 1, n)
                self._blank(i, end)
                i = end
                continue
            opener = self._opener(i, in_define)
            if opener:
                if self._is_doc(i + opener):
                    i = self._read_doc(i, i, opener, False)
                    continue
                m = _RE_DEFINE.match(text, i) if opener == 1 else None
                if m:
                    self.macros.add(m.group(1))
                    self._blank(i, m.end())
                    close = self._scan(m.end(), True)
                    self._blank(close, close + 1)
                    i = close + 1
                    continue
                close, after = self._pragma_close(i, opener)
                self._blank(i, after)
                i = after
                continue
            if in_define:
                if c == '}':
                    return i
                if c == '$':
                    self._blank(i, i + 2)
                    i += 2
                    continue
            i += 1
        if in_define:
            self.errors.append((n - 1, 'unterminated {#define}'))
            return n
        return n


def _line_of(text, offset):
    # type: (str, int) -> int
    return text.count('\n', 0, offset) + 1


def _unterminated_quote(body):
    # type: (str) -> bool
    """Return whether jiepp finds an unterminated string in a doc pragma body.

    jiepp reads ' and " in a doc pragma as the start of a string literal. In a
    string, $ escapes the next character and the other quote is plain text.
    Outside a string, $ is plain text ($27 is the way to write an apostrophe).
    """
    quote = None
    i = 0
    while i < len(body):
        c = body[i]
        if quote is None:
            if c in '\'"':
                quote = c
        elif c == '$':
            i += 1
        elif c == quote:
            quote = None
        i += 1
    return quote is not None


def _first_non_ascii_line(text):
    # type: (str) -> str
    for line in text.splitlines():
        if _RE_NON_ASCII.search(line):
            return ' '.join(line.split())[:60]
    return ''


def collect_macros(root, paths=None):
    # type: (str, list) -> set
    """Return the names defined with {#define} in the given files (default: all sources)."""
    names = set()
    for path in paths if paths is not None else _iter_files(root, _MACRO_DIRS):
        names |= Scan(_read_text(path)).macros
    return names


def lint_text(text, path, macros=frozenset()):
    # type: (str, str, frozenset) -> list
    """Lint one file. path is the repository-relative path with '/' separators."""
    scan = Scan(text)
    known_macros = set(macros) | scan.macros
    findings = []

    def add(rule, offset, message, key=None):
        findings.append(Finding(rule, path, _line_of(text, offset), message, key))

    for offset, message in scan.errors:
        add('parse', offset, message)

    code = scan.code
    for m in _RE_IDENT.finditer(code):
        word = m.group(0)
        start = m.start()
        if start > 0 and code[start - 1] in '#@.':
            # Digits of a based literal (16#FF), a token pasted with @@, or a
            # member name after '.' (a member of a vendor type may be named Max).
            continue
        lower = word.lower()
        if lower == 'continue':
            add('no-continue', start, 'continue is not supported in the OMRON environment')
        if word == lower or word in known_macros:
            continue
        if lower in _LOWERCASE_WORDS or _RE_CONVERSION.match(lower):
            add('keyword-case', start, '{!r} must be written in lowercase ({!r})'.format(word, lower))

    for m in re.finditer(r'/\*', code):
        add('no-c-comment', m.start(), 'use // or (* *) instead of /* */')
    for m in re.finditer(r'\*\)', code):
        add('parse', m.start(), "'*)' without a matching '(*'")

    for doc in scan.docs:
        if doc.style != '(*{doc':
            closing = '}*)' if doc.style.startswith('(*') else '}'
            add('doc-style', doc.start, 'write the doc pragma as (*{doc ...}*), not '
                + doc.style + ' ...' + closing)
        if _unterminated_quote(doc.body):
            add('doc-apostrophe', doc.start,
                'unpaired quote in a doc pragma (jiepp warning PP29); rephrase, '
                "or write $27 for ' and $22 for \"")

    seen = collections.Counter()

    def add_language(offset, text_):
        detail = _first_non_ascii_line(text_)
        seen[detail] += 1
        key = '{}: {}'.format(path, detail)
        if seen[detail] > 1:
            key += ' #{}'.format(seen[detail])
        add('doc-language', offset, 'use English (ASCII) in comments and doc pragmas: '
            + detail, key)

    items = [(d.start, d.body) for d in scan.docs] + [(c.start, c.text) for c in scan.comments]
    for offset, body in sorted(items, key=lambda x: x[0]):
        if _RE_NON_ASCII.search(body):
            add_language(offset, body)

    if path.startswith('src/'):
        doc_ends = set(d.end for d in scan.docs)
        for m in _RE_POU_HEADER.finditer(code):
            start = m.start(1)
            p = start
            while p > 0 and text[p - 1].isspace():
                p -= 1
            if p not in doc_ends:
                add('doc-missing', start, 'POU {} has no doc pragma directly before it'.format(
                    m.group(2)))

    line_comments = [c for c in scan.comments if c.kind == 'line']
    for m in _RE_TEST_BEGIN.finditer(code):
        end_m = _RE_TEST_END.search(code, m.end())
        end = end_m.start() if end_m else len(code)
        has_fact = any(m.end() <= c.start < end and _RE_FACT.match(c.text) for c in line_comments)
        if not has_fact:
            name = m.group(2)
            add('test-fact', m.start(), '{} {} has no "// Fact:" comment'.format(m.group(1), name),
                '{}: {}'.format(path, name))

    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


def _read_text(path):
    # type: (str) -> str
    with open(path, 'rb') as f:
        data = f.read()
    if data.startswith(b'\xef\xbb\xbf'):
        data = data[3:]
    return data.decode('utf-8', errors='replace')


def _iter_files(root, dirs):
    for d in dirs:
        base = os.path.join(root, d)
        if os.path.isfile(base):
            yield base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for name in sorted(filenames):
                if name.endswith('.iec'):
                    yield os.path.join(dirpath, name)


def _rel(root, path):
    # type: (str, str) -> str
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, '/')


def _collect_targets(root, args):
    # type: (str, list) -> list
    if not args:
        return list(_iter_files(root, [d for d in _DEFAULT_DIRS
                                       if os.path.isdir(os.path.join(root, d))]))
    files = []
    for arg in args:
        path = os.path.abspath(arg)
        if not os.path.exists(path):
            raise ValueError('no such file or directory: {}'.format(arg))
        files.extend(_iter_files(root, [path]))
    return files


def xml_entries(root, paths):
    # type: (str, list) -> list
    """Return [(repository-relative path, targets)] of the files compiled by run_tests.py.

    These are the files whose XML --xml-dir expects. With paths, only the
    files under the given files or directories are returned.
    """
    items = run_tests._discover(root)
    if paths:
        prefixes = [os.path.normcase(os.path.abspath(p)) for p in paths]

        def selected(item):
            full = os.path.normcase(os.path.join(root, *item.name.split('/')))
            return any(full == p or full.startswith(p.rstrip(os.sep) + os.sep) for p in prefixes)
        items = [i for i in items if selected(i)]
    return [(i.name, i.targets) for i in items]


def jiecunit_names(root):
    # type: (str) -> tuple
    """Return (POU names, type names) that JiecUnit defines and src/ does not (lowercase)."""
    def names(dirs):
        pous, types = set(), set()
        for path in _iter_files(root, dirs):
            p, t = lint_xml.source_names(Scan(_read_text(path)).code)
            pous |= p
            types |= t
        return pous, types
    vendor_pous, vendor_types = names([os.path.join('vendor', 'jiecunit', 'src'),
                                       os.path.join('vendor', 'jiecunit', 'sys')])
    src_pous, src_types = names(['src'])
    return vendor_pous - src_pous, vendor_types - src_types


def load_baseline_text(text, origin):
    # type: (str, str) -> dict
    """Parse a baseline. Return {rule: set(keys)}. Raise ValueError when it is invalid."""
    try:
        data = json.loads(text)
    except ValueError as e:
        raise ValueError('{} is not valid JSON: {}'.format(origin, e))
    if not isinstance(data, dict):
        raise ValueError('{} must be a JSON object'.format(origin))
    result = {}
    for rule, items in data.items():
        if rule not in WARNING_RULES:
            raise ValueError('{}: unknown warning rule {!r}'.format(origin, rule))
        if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
            raise ValueError('{}: {!r} must be a list of strings'.format(origin, rule))
        result[rule] = set(items)
    return result


def dump_baseline(baseline):
    # type: (dict) -> str
    """Serialize a baseline with one entry per line in a fixed order."""
    data = collections.OrderedDict((r, sorted(baseline[r])) for r in sorted(baseline))
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def baseline_additions(current, base):
    # type: (dict, dict) -> list
    """Return (rule, key) entries of current that are not in base.

    Only the rules present in base are compared, so a pull request may add the
    section of a new rule.
    """
    added = []
    for rule in sorted(base):
        for key in sorted(current.get(rule, set()) - base[rule]):
            added.append((rule, key))
    return added


def _write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def _check_baseline_against(root, rev):
    # type: (str, str) -> int
    path = os.path.join(root, _BASELINE_REL)
    if not os.path.isfile(path):
        print('error: {} does not exist'.format(_BASELINE_REL))
        return 1
    try:
        current = load_baseline_text(_read_text(path), _BASELINE_REL)
    except ValueError as e:
        print('error: {}'.format(e))
        return 1
    try:
        subprocess.check_output(['git', 'rev-parse', '--verify', rev + '^{commit}'], cwd=root,
                                stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError) as e:
        print('error: cannot resolve commit {!r}: {}'.format(rev, e))
        return 2
    # Tell "the file is not in the commit" apart from a failing git command:
    # only the former skips the comparison.
    try:
        listed = subprocess.check_output(['git', 'ls-tree', '--name-only', rev, '--',
                                          _BASELINE_REL], cwd=root, stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError) as e:
        print('error: cannot list {} in {}: {}'.format(_BASELINE_REL, rev, e))
        return 2
    if not listed.strip():
        print('note: {} does not exist in {}; nothing to compare.'.format(_BASELINE_REL, rev))
        return 0
    proc = subprocess.Popen(['git', 'show', '{}:{}'.format(rev, _BASELINE_REL)], cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode != 0:
        print('error: cannot read {} in {}: {}'.format(
            _BASELINE_REL, rev, err.decode('utf-8', errors='replace').strip()))
        return 2
    try:
        base = load_baseline_text(out.decode('utf-8'), '{}:{}'.format(rev, _BASELINE_REL))
    except ValueError as e:
        print('error: {}'.format(e))
        return 1
    added = baseline_additions(current, base)
    for rule, key in added:
        print('error: {}: entry added to {}: {}'.format(rule, _BASELINE_REL, key))
    if added:
        print('The baseline must not grow. Fix the new warnings instead of adding them.')
        return 1
    print('Baseline check passed ({} has no new entries since {}).'.format(_BASELINE_REL, rev))
    return 0


def main(argv=None, root=None):
    # type: (list, str) -> int
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('paths', nargs='*',
                        help='files or directories to check (default: src, test, samples)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--update-baseline', action='store_true',
                      help='remove warnings that no longer occur from the baseline')
    mode.add_argument('--reset-baseline', action='store_true',
                      help='rewrite the baseline from the current warnings '
                           '(only for a pull request that changes a rule)')
    mode.add_argument('--check-baseline-against', metavar='COMMIT',
                      help='fail if the baseline has entries that COMMIT does not have')
    parser.add_argument('--xml-dir', metavar='DIR',
                        help='also check the XML written by run_tests.py --compile-only '
                             '--output-dir DIR (see scripts/lint_xml.py)')
    args = parser.parse_args(argv)
    root = root or _repo_root()
    # Messages quote non-ASCII comments; do not fail on a console that cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')

    if args.check_baseline_against:
        return _check_baseline_against(root, args.check_baseline_against)
    if (args.update_baseline or args.reset_baseline) and args.paths:
        print('error: --update-baseline and --reset-baseline check all files; '
              'do not give paths.', file=sys.stderr)
        return 2

    try:
        files = _collect_targets(root, args.paths)
    except ValueError as e:
        print('error: {}'.format(e), file=sys.stderr)
        return 2
    if not files:
        print('error: no .iec files to check.', file=sys.stderr)
        return 2

    macros = frozenset(collect_macros(root))
    findings = []
    for path in files:
        findings.extend(lint_text(_read_text(path), _rel(root, path), macros))
    checked = set(_rel(root, p) for p in files)

    active_rules = list(SOURCE_WARNING_RULES)
    xml_count = 0
    if args.xml_dir:
        xml_dir = os.path.abspath(args.xml_dir)
        if not os.path.isdir(xml_dir):
            print('error: --xml-dir {}: no such directory'.format(args.xml_dir), file=sys.stderr)
            return 2
        entries = xml_entries(root, args.paths)
        pous, types = jiecunit_names(root)
        xml_findings = lint_xml.check_xml_dir(xml_dir, entries, pous, types,
                                              display_root=os.getcwd())
        findings.extend(xml_findings)
        xml_count = sum(len(targets) for name, targets in entries)
        active_rules.extend(XML_WARNING_RULES)
    # XML keys have no path, so stale XML entries are reported only on a full
    # run that could read every XML. With a missing XML, the warnings in it
    # are unknown, so the baseline must not be rewritten either.
    xml_incomplete = any(f.rule == 'xml-missing' for f in findings)
    xml_full_run = bool(args.xml_dir) and not args.paths and not xml_incomplete
    if xml_incomplete and (args.update_baseline or args.reset_baseline):
        for f in findings:
            if f.rule == 'xml-missing':
                print(f.format(), file=sys.stderr)
        print('error: some XML files are missing; compile them before updating the baseline.',
              file=sys.stderr)
        return 2

    baseline_path = os.path.join(root, _BASELINE_REL)
    baseline = {}
    if os.path.isfile(baseline_path):
        try:
            baseline = load_baseline_text(_read_text(baseline_path), _BASELINE_REL)
        except ValueError as e:
            print('error: {}'.format(e), file=sys.stderr)
            return 2

    current = dict((r, set()) for r in active_rules)
    for f in findings:
        if f.severity == WARNING:
            current[f.rule].add(f.key)

    if args.update_baseline and not os.path.isfile(baseline_path):
        print('error: {} does not exist; create it with --reset-baseline.'.format(_BASELINE_REL),
              file=sys.stderr)
        return 2
    if args.reset_baseline or args.update_baseline:
        # --update-baseline only removes entries from the existing sections. A
        # warning rule without a section is a new rule; its section is created
        # from the current warnings (CI allows a new section, see
        # baseline_additions). The sections of rules that this run did not
        # check (the XML rules without --xml-dir) are kept as they are.
        new = {}
        for rule in WARNING_RULES:
            if rule not in current:
                if rule in baseline:
                    new[rule] = baseline[rule]
                continue
            if args.update_baseline and rule in baseline:
                new[rule] = current[rule] & baseline[rule]
            else:
                new[rule] = current[rule]
        _write_text(baseline_path, dump_baseline(new))
        print('Wrote {} ({} entries).'.format(_BASELINE_REL, sum(len(v) for v in new.values())))
        baseline = new

    errors = [f for f in findings if f.severity == ERROR]
    new_warnings = [f for f in findings
                    if f.severity == WARNING and f.key not in baseline.get(f.rule, set())]
    for f in errors + new_warnings:
        print(f.format())

    stale = []
    for rule, keys in sorted(baseline.items()):
        if rule not in current:
            continue
        for key in sorted(keys - current[rule]):
            if rule in XML_WARNING_RULES:
                if xml_full_run:
                    stale.append((rule, key))
            elif key.split(': ', 1)[0] in checked:
                stale.append((rule, key))
    for rule, key in stale:
        print('note: {}: no longer occurs: {}'.format(rule, key))
    if stale:
        print('note: run "python scripts/lint.py --update-baseline" to remove the fixed warnings '
              'from {}.'.format(_BASELINE_REL))

    baselined = sum(1 for f in findings if f.severity == WARNING) - len(new_warnings)
    xml_note = ' and {} XML files'.format(xml_count) if args.xml_dir else ''
    print('lint: {} files{}, {} errors, {} new warnings, {} warnings in the baseline.'.format(
        len(files), xml_note, len(errors), len(new_warnings), baselined))
    if errors or new_warnings:
        return 1
    print('Lint passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
