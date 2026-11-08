#!/usr/bin/env python
# coding: utf-8
"""List the public POUs of JiecLib that no test calls.

Reads the omron XML that `python scripts/run_tests.py --compile-only
--output-dir DIR` wrote (DIR/omron/<path>.xml) and the sources.

Each Function and FunctionBlock in the XML is classified as:
  library   It is in the XML of a source entry file (src/...), so the
            library provides it as it is: the functions of src/ and the
            template instances that src/ makes (Array_bubblesort_dint, ...).
            Each one needs a test.
  template  It is only in the XML of the tests, and its name has the form of
            a name made by a template ("HashMap_*_copy", from a macro such as
            {#define _HASHMAP_COPY_(T) HashMap_@@T@@_copy} in src/). The
            instances are made by the users, so the operation needs a test
            through any one instance.
  helper    It is defined in a test source (test/...).
  jiecunit  It is a POU of JiecUnit (defined in vendor/jiecunit and not in
            src/, or named JiecTest_*).
  unclassified  None of the above. --check fails, so that a new kind of
            name (for example a template whose form is not recognized) is
            not skipped silently.

A POU (or a template operation) is tested when its name is called in the
body of a test program (a Program element of a test XML; comments and
strings are ignored): only "name(" counts, not a variable, a member or a
named argument with the name of a POU. A function block counts as tested when
a test program declares a variable of its type (it is used through the
instance). POUs whose name contains "private" or "_static_" are internal and
need no test.

scripts/pou_inventory_allow.txt lists the names (or template forms, such as
HashMap_*_copy) that may stay without a test, one per line with a reason:
  <name or form> <reason>
--check exits with 1 when an untested public POU is not in the list, when a
POU is unclassified, or when a line of the list is stale (the POU no longer
exists, or it has a test now) or has no reason.

Usage:
  python scripts/run_tests.py --compile-only --output-dir out
  python scripts/pou_inventory.py --xml-dir out
  python scripts/pou_inventory.py --xml-dir out --check
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import lint  # noqa: E402
import lint_xml  # noqa: E402
import run_tests  # noqa: E402

_NS = '{www.iec.ch/public/TC65SC65BWG7TF10}'
_TARGET = 'omron'
_ALLOW_REL = 'scripts/pou_inventory_allow.txt'

# A macro that builds a name by token pasting: {#define NAME(T) HashMap_@@T@@_copy}
_RE_NAME_MACRO = re.compile(r'\{#define[ \t]+\w+\(([\w, \t]*)\)[ \t]+([\w@]*@@[\w@]*)[ \t]*\}')
_RE_IDENT = re.compile(r'[A-Za-z_]\w*')


def template_forms(texts):
    # type: (list) -> dict
    """Return {form: regex} for the names that the macros of texts build.

    In "HashMap_@@T@@_copy" with the macro parameter T, the parameter is any
    name, so the form is "HashMap_*_copy".
    """
    forms = {}
    for text in texts:
        for m in _RE_NAME_MACRO.finditer(text):
            params = set(p.strip() for p in m.group(1).split(',') if p.strip())
            parts = m.group(2).split('@@')
            pieces = []
            for part in parts:
                pieces.append('*' if part in params else part)
            form = ''.join(pieces)
            if '*' not in form or not form.replace('*', ''):
                continue
            pattern = '^' + '.+'.join(re.escape(p) for p in form.split('*')) + '$'
            forms[form] = re.compile(pattern, re.I)
    return forms


def match_form(name, forms):
    # type: (str, dict) -> str
    """Return the most general form that matches name, or ''.

    A template that uses another template makes names of both forms: the
    hash set makes HashMap_HSIT<name>_clear, which matches HashMap_HSIT*_clear
    and HashMap_*_clear. The operation is "clear of the hash map", so the most
    general form (the fewest fixed characters) is used.
    """
    matches = [form for form, regex in forms.items() if regex.match(name)]
    if not matches:
        return ''
    return min(matches, key=lambda f: (len(f.replace('*', '')), f))


def is_internal(name):
    # type: (str) -> bool
    lower = name.lower()
    return 'private' in lower or '_static_' in lower


def read_allow(path):
    # type: (str) -> tuple
    """Return ({name or form: reason}, errors)."""
    allow = {}
    errors = []
    if not os.path.isfile(path):
        return allow, ['{}: no such file'.format(path)]
    with open(path, encoding='utf-8-sig') as f:
        for number, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            fields = stripped.split(None, 1)
            if len(fields) < 2:
                errors.append('{}:{}: {} has no reason'.format(path, number, fields[0]))
                continue
            if fields[0] in allow:
                errors.append('{}:{}: {} is listed twice'.format(path, number, fields[0]))
                continue
            allow[fields[0]] = fields[1]
    return allow, errors


class Inventory(object):
    """The POUs found in the XML, their classes and whether a test calls them."""

    def __init__(self):
        self.kind = {}        # name -> class
        self.form = {}        # name -> template form (class template)
        self.where = {}       # name -> first XML where it was found
        self.called = set()   # lowercase names called by test programs
        self.missing = []     # XML that were expected but not found

    def untested(self):
        # type: () -> tuple
        """Return (untested library POUs, untested template forms)."""
        pous = sorted(n for n, k in self.kind.items()
                      if k == 'library' and not is_internal(n) and n.lower() not in self.called)
        forms = {}
        for name, kind in self.kind.items():
            if kind != 'template':
                continue
            form = self.form[name]
            forms.setdefault(form, False)
            if name.lower() in self.called:
                forms[form] = True
        untested_forms = sorted(f for f, tested in forms.items()
                                if not tested and not is_internal(f))
        return pous, untested_forms

    def unclassified(self):
        # type: () -> list
        return sorted(n for n, k in self.kind.items() if k == 'unclassified')

    def known(self):
        # type: () -> set
        """Return the names and template forms that exist."""
        names = set(n for n, k in self.kind.items() if k == 'library')
        names |= set(self.form.values())
        return names

    def tested(self, entry):
        # type: (str) -> bool
        """Tell whether a name or a template form of the allow list is tested."""
        if '*' in entry:
            return any(self.form.get(n) == entry and n.lower() in self.called
                       for n in self.kind)
        return entry.lower() in self.called


def _source_names(root, dirs):
    # type: (str, list) -> tuple
    pous = set()
    texts = []
    for path in lint._iter_files(root, dirs):
        text = lint._read_text(path)
        texts.append(text)
        p, t = lint_xml.source_names(lint.Scan(text).code)
        pous |= p
    return pous, texts


# A call: a name followed by "(", not a member after ".".
_RE_CALL = re.compile(r'(?<![.\w])([A-Za-z_]\w*)\s*\(')


def _called_names(st_text):
    # type: (str) -> set
    """Return the names called in an ST body (comments and strings ignored).

    Only "name(" counts, so a local variable or a member with the name of a
    POU does not make the POU tested.
    """
    code = lint.Scan(st_text).code
    return set(m.group(1).lower() for m in _RE_CALL.finditer(code))


def _declared_types(program):
    # type: (ET.Element) -> set
    """Return the type names of the variables of a test program.

    A function block is used through an instance, declared with its type
    name, so the type names count as used.
    """
    names = set()
    for var in program.iter(_NS + 'Variable'):
        for type_name in var.iter(_NS + 'TypeName'):
            names.add((type_name.text or '').strip().lower())
    return names


def build(root, xml_dir):
    # type: (str, str) -> Inventory
    inv = Inventory()
    src_pous, src_texts = _source_names(root, ['src'])
    test_pous, test_texts = _source_names(root, ['test'])
    forms = template_forms(src_texts)
    jiecunit_pous, jiecunit_types = lint.jiecunit_names(root)

    found = {}  # name -> (in a src XML, first XML)
    for item in run_tests._discover(root):
        # The examples in samples/ are not part of the library.
        if _TARGET not in item.targets or item.name.startswith('samples/'):
            continue
        path = lint_xml.expected_xml(xml_dir, item.name, _TARGET)
        if not os.path.isfile(path):
            inv.missing.append('no XML: {}'.format(path))
            continue
        try:
            tree = ET.parse(path)
        except (ET.ParseError, IOError, OSError) as e:
            inv.missing.append('cannot read the XML {}: {}'.format(path, e))
            continue
        for tag in ('Function', 'FunctionBlock'):
            for pou in tree.iter(_NS + tag):
                name = pou.get('name', '')
                in_src, first = found.get(name, (False, path))
                found[name] = (in_src or item.name.startswith('src/'), first)
        if item.kind == 'test':
            for program in tree.iter(_NS + 'Program'):
                for st in program.iter(_NS + 'ST'):
                    inv.called |= _called_names(st.text or '')
                inv.called |= _declared_types(program)

    for name, (in_src, first) in found.items():
        lower = name.lower()
        inv.where[name] = first
        # The order matters: a POU in the XML of src/ is always a library POU,
        # and a name defined in src/ is never taken for a template instance.
        if in_src:
            kind = 'library'
        elif lower.startswith('jiectest_') or lower in jiecunit_pous:
            kind = 'jiecunit'
        elif lower in src_pous:
            kind = 'library'
        elif lower in test_pous:
            kind = 'helper'
        else:
            form = match_form(name, forms)
            if form:
                kind = 'template'
                inv.form[name] = form
            else:
                kind = 'unclassified'
        inv.kind[name] = kind
    return inv


def main(argv=None, root=None):
    # type: (list, str) -> int
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--xml-dir', required=True, metavar='DIR',
                        help='the --output-dir of run_tests.py --compile-only')
    parser.add_argument('--check', action='store_true',
                        help='fail on untested POUs that are not in {}, unclassified POUs '
                             'and stale lines'.format(_ALLOW_REL))
    args = parser.parse_args(argv)
    root = root or run_tests._repo_root()
    if not os.path.isdir(args.xml_dir):
        print('error: --xml-dir {}: no such directory'.format(args.xml_dir), file=sys.stderr)
        return 2

    inv = build(root, os.path.abspath(args.xml_dir))
    if inv.missing:
        for message in inv.missing:
            print('error: {}'.format(message))
        print('Compile with "python scripts/run_tests.py --compile-only --output-dir DIR".')
        return 2

    pous, forms = inv.untested()
    untested = pous + forms
    counts = {}
    for kind in inv.kind.values():
        counts[kind] = counts.get(kind, 0) + 1
    print('POUs: ' + ', '.join('{} {}'.format(counts[k], k) for k in sorted(counts)))
    print('Template operations: {}'.format(len(set(inv.form.values()))))

    allow, errors = read_allow(os.path.join(root, *_ALLOW_REL.split('/')))
    problems = list(errors)
    for name in inv.unclassified():
        problems.append('unclassified POU {} (in {}): add its template form or move it'.format(
            name, os.path.relpath(inv.where[name], args.xml_dir).replace(os.sep, '/')))
    for name in untested:
        if name not in allow:
            problems.append('{} has no test: write one, or add it to {} with a reason'.format(
                name, _ALLOW_REL))
    known = inv.known()
    untested_set = set(untested)
    for entry in sorted(allow):
        if entry in untested_set:
            continue
        if entry in known and not inv.tested(entry):
            continue  # an internal or allowed entry that exists and has no test
        if entry not in known:
            problems.append('{}: {} does not exist; remove the line'.format(_ALLOW_REL, entry))
        else:
            problems.append('{}: {} has a test now; remove the line'.format(_ALLOW_REL, entry))

    print('Untested public POUs and template operations: {} ({} in {})'.format(
        len(untested), len([n for n in untested if n in allow]), _ALLOW_REL))
    for name in untested:
        reason = allow.get(name)
        print('  {}{}'.format(name, '  # ' + reason if reason else ''))
    for line in problems:
        print('error: pou-inventory: {}'.format(line))
    if args.check and problems:
        return 1
    if args.check:
        print('POU inventory check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
