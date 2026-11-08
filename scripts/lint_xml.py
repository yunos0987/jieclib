# coding: utf-8
"""The lint rules that read the compiled XML (scripts/lint.py --xml-dir DIR).

DIR is the output of `python scripts/run_tests.py --compile-only --output-dir
DIR`: DIR/<target>/<path of the .iec file>.xml. The XML has every POU,
variable and structure member after preprocessing, so names made by the
templates are checked too.

Rules (rule id, severity):
  xml-missing         error    An XML file expected from the header of a file
                               (one per declared target) is missing, or cannot
                               be read. The rules do not pass silently when a
                               compile failed.
  pou-name-length     error    A POU name is at most 64 bytes (KEYENCE).
  reserved-name       error    left, right, len, cmp and dec are not used as
                               variable or member names (IEC 61131-3, OMRON).
  omron-p-prefix      error    No variable or member name starts with p_ or P_
                               (OMRON).
  varlen-array-inout  error    A variable-length array (array[*]) is used only
                               as a var_in_out parameter.
  no-struct-return    error    A function does not return a structure (OMRON).
  no-alias-type       error    No directly derived (alias) type
                               ("type name : dint; end_type") is declared
                               (OMRON).
  keyence-names       warning  In the files that declare the keyence or the
                               mitsubishi target: no one-letter name, no
                               variable name that starts with h or H and has
                               no "_", and no variable name like r1, T2 or c10
                               (^[rRtTcC][0-9]+$).

The names checked are the Variable elements of every Function and
FunctionBlock (parameters, local and temporary variables) and the Member
elements of the structures. Programs (the test programs) and the global
variables of a Configuration (only the tests have one) are not checked.
The POUs and types of JiecUnit (defined in vendor/jiecunit and not in src/,
or named JiecTest_*) are not checked either.

A POU is in the XML of every file that includes it, so findings are reported
once per rule, POU and name, with the first XML where they were found:
  <xml>: <severity>: <rule>: <POU>.<name>: <message>
The baseline key of keyence-names is "<POU>.<name>".
"""
import os
import re
import xml.etree.ElementTree as ET

_NS = '{www.iec.ch/public/TC65SC65BWG7TF10}'
_XSI_TYPE = '{http://www.w3.org/2001/XMLSchema-instance}type'

ERROR = 'error'
WARNING = 'warning'

RULES = (
    ('xml-missing', ERROR),
    ('pou-name-length', ERROR),
    ('reserved-name', ERROR),
    ('omron-p-prefix', ERROR),
    ('varlen-array-inout', ERROR),
    ('no-struct-return', ERROR),
    ('no-alias-type', ERROR),
    ('keyence-names', WARNING),
)

_MAX_POU_NAME_BYTES = 64
_RESERVED = frozenset(['left', 'right', 'len', 'cmp', 'dec'])
_KEYENCE_TARGETS = frozenset(['keyence', 'mitsubishi'])
_RE_KEYENCE_REGISTER = re.compile(r'^[rRtTcC][0-9]+$')
_RE_POU = re.compile(r'(?im)^[ \t]*(?:function_block|function)[ \t]+([A-Za-z_]\w*)')
_RE_TYPE_BLOCK = re.compile(r'(?is)\btype\b(.*?)\bend_type\b')
_RE_TYPE_NAME = re.compile(r'(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*:')


def keyence_name_problem(name, variable=True):
    # type: (str, bool) -> str
    """Return why name breaks the KEYENCE naming rules, or '' when it does not.

    CONTRIBUTING.md forbids one-letter names for every element, and the h/H
    and ^[rRtTcC][0-9]+$ names for variables only, so a structure member
    (variable=False) is checked for the first rule only.
    """
    if re.match(r'^[A-Za-z]$', name):
        return 'one-letter name'
    if not variable:
        return ''
    if name[:1] in ('h', 'H') and '_' not in name:
        return 'starts with h/H and has no "_"'
    if _RE_KEYENCE_REGISTER.match(name):
        return 'looks like a device name (^[rRtTcC][0-9]+$)'
    return ''


def source_names(code):
    # type: (str) -> tuple
    """Return (POU names, type names) defined in code (comments and strings masked)."""
    pous = set(m.group(1).lower() for m in _RE_POU.finditer(code))
    types = set()
    for block in _RE_TYPE_BLOCK.finditer(code):
        types.update(m.group(1).lower() for m in _RE_TYPE_NAME.finditer(block.group(1)))
    return pous, types


class XmlFinding(object):
    """One violation found in the XML. key is "<POU>.<name>" (the baseline key)."""

    def __init__(self, rule, severity, xml, key, message):
        # type: (str, str, str, str, str) -> None
        self.rule = rule
        self.severity = severity
        self.path = xml
        self.line = 0
        self.key = key
        self.message = message

    def format(self):
        # type: () -> str
        if self.key:
            return '{}: {}: {}: {}: {}'.format(self.path, self.severity, self.rule, self.key,
                                               self.message)
        return '{}: {}: {}: {}'.format(self.path, self.severity, self.rule, self.message)


def _local(tag):
    # type: (str) -> str
    return tag[len(_NS):] if tag.startswith(_NS) else tag


def _is_varlen(type_element):
    # type: (ET.Element) -> bool
    return type_element is not None and type_element.find('.//' + _NS + 'VariableLength') is not None


def _variables(pou):
    # type: (ET.Element) -> list
    """Return [(section, Variable element)] of a Function or FunctionBlock."""
    found = []
    for section in pou.iter():
        name = _local(section.tag)
        if name in ('InputVars', 'OutputVars', 'InoutVars', 'Vars', 'TempVars',
                    'ExternalVars'):
            for var in section.findall(_NS + 'Variable'):
                found.append((name, var))
    return found


class XmlChecker(object):
    """Collects the findings of all the XML files, without duplicates."""

    def __init__(self, excluded_pous, excluded_types):
        # type: (set, set) -> None
        self.excluded_pous = set(n.lower() for n in excluded_pous)
        self.excluded_types = set(n.lower() for n in excluded_types)
        self.findings = []
        self._seen = set()

    def _excluded(self, name, kinds):
        # type: (str, set) -> bool
        lower = name.lower()
        return lower.startswith('jiectest_') or lower in kinds

    def _add(self, rule, severity, xml, key, message):
        # type: (str, str, str, str, str) -> None
        if (rule, key) in self._seen:
            return
        self._seen.add((rule, key))
        self.findings.append(XmlFinding(rule, severity, xml, key, message))

    def missing(self, xml, message):
        # type: (str, str) -> None
        self.findings.append(XmlFinding('xml-missing', ERROR, xml, '', message))

    def check(self, xml, display, keyence):
        # type: (str, str, bool) -> None
        """Check one XML file. keyence turns on the keyence-names rule."""
        try:
            tree = ET.parse(xml)
        except (ET.ParseError, IOError, OSError) as e:
            self.missing(display, 'cannot read the XML: {}'.format(e))
            return
        types = {}
        for decl in tree.iter(_NS + 'DataTypeDecl'):
            spec = decl.find(_NS + 'UserDefinedTypeSpec')
            types[decl.get('name', '').lower()] = spec.get(_XSI_TYPE, '') if spec is not None else ''
        for decl in tree.iter(_NS + 'DataTypeDecl'):
            self._check_type(decl, display, keyence)
        for tag in ('Function', 'FunctionBlock'):
            for pou in tree.iter(_NS + tag):
                self._check_pou(pou, tag, types, display, keyence)

    def _check_name(self, owner, name, display, keyence, variable=True):
        # type: (str, str, str, bool, bool) -> None
        key = '{}.{}'.format(owner, name)
        if name.lower() in _RESERVED:
            self._add('reserved-name', ERROR, display, key,
                      '"{}" is reserved (CONTRIBUTING.md, 命名規則)'.format(name))
        if name[:2] in ('p_', 'P_'):
            self._add('omron-p-prefix', ERROR, display, key,
                      'names must not start with p_ or P_ (OMRON)')
        if keyence:
            problem = keyence_name_problem(name, variable)
            if problem:
                self._add('keyence-names', WARNING, display, key,
                          '{} (KEYENCE / Mitsubishi naming rule)'.format(problem))

    def _check_type(self, decl, display, keyence):
        # type: (ET.Element, str, bool) -> None
        name = decl.get('name', '')
        if self._excluded(name, self.excluded_types):
            return
        spec = decl.find(_NS + 'UserDefinedTypeSpec')
        kind = spec.get(_XSI_TYPE, '') if spec is not None else ''
        if kind == 'DirectlyDerivedTypeSpec':
            self._add('no-alias-type', ERROR, display, name,
                      'directly derived (alias) types are not supported by OMRON')
        if spec is None:
            return
        for member in spec.findall(_NS + 'Member'):
            member_name = member.get('name', '')
            self._check_name(name, member_name, display, keyence, variable=False)
            if _is_varlen(member.find(_NS + 'Type')):
                self._add('varlen-array-inout', ERROR, display, '{}.{}'.format(name, member_name),
                          'a variable-length array can only be a var_in_out parameter')

    def _check_pou(self, pou, tag, types, display, keyence):
        # type: (ET.Element, str, dict, str, bool) -> None
        name = pou.get('name', '')
        if self._excluded(name, self.excluded_pous):
            return
        if len(name.encode('utf-8')) > _MAX_POU_NAME_BYTES:
            self._add('pou-name-length', ERROR, display, name,
                      'the name is {} bytes; at most {} (KEYENCE)'.format(
                          len(name.encode('utf-8')), _MAX_POU_NAME_BYTES))
        if tag == 'Function':
            result = pou.find(_NS + 'ResultType/' + _NS + 'TypeName')
            if result is not None and types.get((result.text or '').strip().lower()) == \
                    'StructTypeSpec':
                self._add('no-struct-return', ERROR, display, name,
                          'returns the structure {}; return it through var_in_out '
                          '(OMRON)'.format(result.text.strip()))
        for section, var in _variables(pou):
            var_name = var.get('name', '')
            self._check_name(name, var_name, display, keyence)
            if section != 'InoutVars' and _is_varlen(var.find(_NS + 'Type')):
                self._add('varlen-array-inout', ERROR, display, '{}.{}'.format(name, var_name),
                          'a variable-length array can only be a var_in_out parameter '
                          '(found in {})'.format(section))


def expected_xml(xml_dir, item_name, target):
    # type: (str, str, str) -> str
    """Return the XML path that run_tests.py --output-dir writes for item_name and target."""
    stem = item_name[:-4] if item_name.endswith('.iec') else item_name
    return os.path.join(xml_dir, target, *(stem + '.xml').split('/'))


def check_xml_dir(xml_dir, items, excluded_pous, excluded_types, display_root=None):
    # type: (str, list, set, set, str) -> list
    """Check the XML of items ([(repository-relative path, [targets])]). Return the findings."""
    checker = XmlChecker(excluded_pous, excluded_types)
    for name, targets in items:
        for target in targets:
            path = expected_xml(xml_dir, name, target)
            display = path
            if display_root:
                try:
                    display = os.path.relpath(path, display_root)
                except ValueError:
                    pass  # another drive on Windows
            display = display.replace(os.sep, '/')
            if not os.path.isfile(path):
                checker.missing(display, 'no XML for {} ({}); compile it with run_tests.py '
                                         '--compile-only --output-dir'.format(name, target))
                continue
            checker.check(path, display, target in _KEYENCE_TARGETS)
    return checker.findings
