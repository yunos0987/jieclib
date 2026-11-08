#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/pou_inventory.py.

The tests build a small repository and hand-written XML in the form that
jiecc writes (only the elements that pou_inventory.py reads).

Usage:
  python scripts/test_pou_inventory.py
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

import pou_inventory  # noqa: E402

_HEADER = '(*\n * $ jiecc ./x.iec -o ./x.xml -t omron\n *)\n'


def _xml(functions=(), programs=()):
    """Return a jiecc-like XML with the given functions and {program name: ST body}."""
    body = []
    for name in functions:
        body.append('<Function name="{}"><MainBody><BodyContent><ST>;</ST></BodyContent>'
                    '</MainBody></Function>'.format(name))
    for name, st in programs:
        body.append('<Program name="{}"><MainBody><BodyContent><ST>{}</ST></BodyContent>'
                    '</MainBody></Program>'.format(name, st))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<Project xmlns="www.iec.ch/public/TC65SC65BWG7TF10"><Types><GlobalNamespace>'
            + ''.join(body) + '</GlobalNamespace></Types></Project>\n')


class InventoryTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.write('src/a/a.iec', _HEADER + 'function A_used: dint\nend\n'
                   'function A_unused: dint\nend\nfunction A_private_x: dint\nend\n')
        self.write('src/t/t_template.iec', '{#define _T_COPY_(T) Tpl_@@T@@_copy}\n'
                   '{#define _T_CLEAR_(T) Tpl_@@T@@_clear}\n')
        self.write('test/test_x.iec', 'DEFINE_CONFIGURATION\nfunction Helper_fn: dint\nend\n')
        self.write('out/omron/src/a/a.xml', _xml(['A_used', 'A_unused', 'A_private_x']))
        self.set_test_xml('A_used(); Tpl_int_copy();')
        self.write('scripts/pou_inventory_allow.txt', '# none\n')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def set_test_xml(self, st, extra=()):
        functions = ['Tpl_int_copy', 'Tpl_real_copy', 'Tpl_int_clear', 'Helper_fn',
                     'JiecTest_x'] + list(extra)
        self.write('out/omron/test/test_x.xml', _xml(functions, [('test_x', st)]))

    def build(self):
        return pou_inventory.build(self.root, os.path.join(self.root, 'out'))

    def check(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = pou_inventory.main(['--xml-dir', os.path.join(self.root, 'out'), '--check'],
                                      root=self.root)
        return code, out.getvalue()

    def test_classes(self):
        inv = self.build()
        self.assertEqual('library', inv.kind['A_used'])
        self.assertEqual('template', inv.kind['Tpl_real_copy'])
        self.assertEqual('Tpl_*_copy', inv.form['Tpl_real_copy'])
        self.assertEqual('helper', inv.kind['Helper_fn'])
        self.assertEqual('jiecunit', inv.kind['JiecTest_x'])
        self.assertEqual([], inv.unclassified())

    def test_untested(self):
        # A_private_x is internal; Tpl_*_copy is tested through Tpl_int_copy.
        self.assertEqual((['A_unused'], ['Tpl_*_clear']), self.build().untested())

    def test_comments_and_strings_are_not_calls(self):
        self.set_test_xml("A_used(); Tpl_int_copy(); // A_unused\n s := 'Tpl_int_clear';")
        self.assertEqual((['A_unused'], ['Tpl_*_clear']), self.build().untested())

    def test_variables_members_and_named_arguments_are_not_calls(self):
        self.set_test_xml('A_used(); Tpl_int_copy(); x := A_unused; y.A_unused(); '
                          'z(A_unused:=1);')
        self.assertEqual((['A_unused'], ['Tpl_*_clear']), self.build().untested())

    def test_declared_function_block_type_is_used(self):
        program = ('<Program name="test_x"><Vars><Variable name="inst"><Type>'
                   '<TypeName>A_unused</TypeName></Type></Variable></Vars><MainBody>'
                   '<BodyContent><ST>A_used(); Tpl_int_copy(); inst();</ST></BodyContent>'
                   '</MainBody></Program>')
        xml = _xml(['Tpl_int_copy', 'Tpl_int_clear']).replace(
            '</GlobalNamespace>', program + '</GlobalNamespace>')
        self.write('out/omron/test/test_x.xml', xml)
        self.assertEqual(([], ['Tpl_*_clear']), self.build().untested())

    def test_a_name_defined_in_src_is_not_a_template_instance(self):
        # Tpl_x_copy matches Tpl_*_copy, but src/ defines it, so it is a
        # library POU that needs its own test.
        self.write('src/t/extra.iec', 'function Tpl_x_copy: dint\nend\n')
        self.set_test_xml('A_used(); Tpl_int_copy();', ['Tpl_x_copy'])
        inv = self.build()
        self.assertEqual('library', inv.kind['Tpl_x_copy'])
        self.assertIn('Tpl_x_copy', inv.untested()[0])

    def test_broken_xml_is_an_error(self):
        self.write('out/omron/test/test_x.xml', '<Project')
        code, out = self.check()
        self.assertEqual(2, code, out)
        self.assertIn('cannot read', out)

    def test_check_needs_the_allow_list(self):
        code, out = self.check()
        self.assertEqual(1, code, out)
        self.assertIn('A_unused has no test', out)
        self.write('scripts/pou_inventory_allow.txt',
                   'A_unused Tested later.\nTpl_*_clear Tested later.\n')
        code, out = self.check()
        self.assertEqual(0, code, out)

    def test_unclassified_fails(self):
        self.set_test_xml('A_used(); Tpl_int_copy(); Tpl_int_clear(); A_unused();', ['Mystery_fn'])
        code, out = self.check()
        self.assertEqual(1, code, out)
        self.assertIn('unclassified POU Mystery_fn', out)

    def test_stale_and_bad_lines_fail(self):
        base = 'A_unused Later.\nTpl_*_clear Later.\n'
        cases = ((base + 'A_used Tested already.\n', 'has a test now'),
                 (base + 'Gone_fn Removed.\n', 'does not exist'),
                 (base + 'Tpl_*_copy Tested already.\n', 'has a test now'),
                 ('A_unused\nTpl_*_clear Later.\n', 'has no reason'),
                 (base + 'A_unused Twice.\n', 'listed twice'))
        for text, message in cases:
            with self.subTest(text=text):
                self.write('scripts/pou_inventory_allow.txt', text)
                code, out = self.check()
                self.assertEqual(1, code, out)
                self.assertIn(message, out)

    def test_missing_xml_is_an_error(self):
        os.remove(os.path.join(self.root, 'out', 'omron', 'test', 'test_x.xml'))
        code, out = self.check()
        self.assertEqual(2, code, out)


class FormTest(unittest.TestCase):

    def test_template_forms(self):
        forms = pou_inventory.template_forms([
            '{#define _A_(T) HashMap_@@T@@_copy}\n{#define _B_(P) P@@_nextGaussian}\n'
            '{#define _C_(T) Array_sort_@@T}\n{#define NAME_ONLY(T) T}\n'])
        self.assertEqual({'HashMap_*_copy', '*_nextGaussian', 'Array_sort_*'}, set(forms))

    def test_the_most_general_form_wins(self):
        forms = pou_inventory.template_forms([
            '{#define _A_(T) HashMap_@@T@@_clear}\n{#define _B_(T) HashMap_HSIT@@T@@_clear}\n'])
        self.assertEqual('HashMap_*_clear', pou_inventory.match_form('HashMap_HSITdint_clear',
                                                                     forms))
        self.assertEqual('', pou_inventory.match_form('Other_clear', forms))


if __name__ == '__main__':
    unittest.main()
