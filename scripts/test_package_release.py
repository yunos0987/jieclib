#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/package_release.py.

Usage:
  python scripts/test_package_release.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import package_release  # noqa: E402


def _write(root, rel, text):
    path = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


class CheckTagTest(unittest.TestCase):

    def test_tag_must_be_v_and_version(self):
        self.assertTrue(package_release.check_tag('v4.1.0', '4.1.0'))
        for tag in ('4.1.0', 'v4.1.1', 'v4.1.0-rc1', 'V4.1.0', 'v4.1.0 ', ''):
            with self.subTest(tag=tag):
                self.assertFalse(package_release.check_tag(tag, '4.1.0'))

    def test_command_uses_the_version_file(self):
        version = package_release.read_version()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, package_release.main(['check-tag', 'v' + version]))
            self.assertEqual(1, package_release.main(['check-tag', 'v0.0.0-test']))


class PackageTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.xml = os.path.join(self.tmp, 'out')
        self.dist = os.path.join(self.tmp, 'dist')
        _write(self.xml, 'omron/src/math/floor.xml', '<omron/>')
        _write(self.xml, 'omron/src/sys.xml', '<sys/>')
        _write(self.xml, 'omron/test/math/test_floor.xml', '<test/>')
        _write(self.xml, 'keyence/src/array/array.xml', '<keyence/>')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zips_per_target_with_paths_relative_to_src(self):
        made = package_release.package(self.xml, self.dist, '4.1.0', 'Jiecc 9.2.0')
        self.assertEqual(['jieclib-4.1.0-omron.zip', 'jieclib-4.1.0-keyence.zip'],
                         [os.path.basename(p) for p in made])
        with zipfile.ZipFile(made[0]) as zf:
            self.assertEqual(['math/floor.xml', 'sys.xml', 'IMPORT_NOTES.txt'], zf.namelist())
            notes = zf.read('IMPORT_NOTES.txt').decode('utf-8')
        self.assertIn('Jiecc 9.2.0', notes)
        self.assertIn('-t omron', notes)
        self.assertIn('v4.1.0', notes)
        with zipfile.ZipFile(made[1]) as zf:
            self.assertEqual(['array/array.xml', 'IMPORT_NOTES.txt'], zf.namelist())

    def test_a_target_without_xml_is_an_error(self):
        shutil.rmtree(os.path.join(self.xml, 'keyence'))
        with self.assertRaises(ValueError):
            package_release.package(self.xml, self.dist, '4.1.0', 'Jiecc 9.2.0')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = package_release.main(['package', '--xml-dir', self.xml, '--dist', self.dist,
                                         '--version', '4.1.0', '--jiecc-version', 'x'])
        self.assertEqual(1, code)


if __name__ == '__main__':
    unittest.main()
