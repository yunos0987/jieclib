#!/usr/bin/env python
# coding: utf-8
"""Unit tests for scripts/check_pr_body.py.

Usage:
  python scripts/test_check_pr_body.py
"""
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import check_pr_body  # noqa: E402

_TEMPLATE = os.path.join(os.path.dirname(_HERE), '.github', 'pull_request_template.md')

_HEADER_KEYENCE = '(*\n * $ jiecc ./x.iec -o ./x.xml -t keyence\n * $ jiecc ./x.iec -o ./x.xml -t omron\n *)\n'
_HEADER_OMRON = '(*\n * $ jiecc ./x.iec -o ./x.xml -t omron\n *)\n'


def _template():
    with open(_TEMPLATE, encoding='utf-8') as f:
        return f.read()


def _fill(body, level, **fields):
    """Fill the fields of one section of the template."""
    head, sep, rest = body.partition('## ' + level + ' ')
    title, nl, section = rest.partition('\n')
    lines = []
    for line in section.split('\n'):
        for name, value in fields.items():
            if line.startswith('- {}:'.format(name)):
                line = '- {}: {}'.format(name, value)
        lines.append(line)
    return head + sep + title + nl + '\n'.join(lines)


class SectionTest(unittest.TestCase):

    def test_template_has_empty_l3_and_l4_sections(self):
        sections = check_pr_body.parse_sections(_template())
        self.assertEqual(['L3', 'L4'], sorted(sections))
        for level in ('L3', 'L4'):
            self.assertEqual('', sections[level]['結果'])
            self.assertTrue(check_pr_body.check_section(level, sections[level]))

    def test_passed_needs_environment_and_files(self):
        body = _fill(_template(), 'L3', 結果='合格')
        errors = check_pr_body.check_section('L3', check_pr_body.parse_sections(body)['L3'])
        self.assertEqual(2, len(errors), errors)
        body = _fill(body, 'L3', 開発環境と版='Sysmac Studio 1.62',
                     実行したテストファイル='test/math/test_floor.iec')
        self.assertEqual([], check_pr_body.check_section(
            'L3', check_pr_body.parse_sections(body)['L3']))

    def test_not_run_needs_a_reason(self):
        body = _fill(_template(), 'L4', 結果='未実施')
        sections = check_pr_body.parse_sections(body)
        self.assertEqual(1, len(check_pr_body.check_section('L4', sections['L4'])))
        body = _fill(body, 'L4', 未実施の理由='KV Studio を使えないため')
        sections = check_pr_body.parse_sections(body)
        self.assertEqual([], check_pr_body.check_section('L4', sections['L4']))

    def test_unknown_result_is_an_error(self):
        body = _fill(_template(), 'L3', 結果='OK', 開発環境と版='x', 実行したテストファイル='y')
        sections = check_pr_body.parse_sections(body)
        self.assertEqual(1, len(check_pr_body.check_section('L3', sections['L3'])))

    def test_missing_section_is_an_error(self):
        self.assertEqual(1, len(check_pr_body.check_section('L3', None)))

    def test_values_in_comments_are_ignored(self):
        body = '## L3 x\n\n- 結果: <!-- 合格 -->\n'
        sections = check_pr_body.parse_sections(body)
        self.assertEqual('', sections['L3']['結果'])

    def test_indented_lines_continue_a_field(self):
        body = ('## L3 x\n\n- 結果: 合格\n- 開発環境と版: Sysmac Studio 1.62\n'
                '- 実行したテストファイル:\n  - test/a.iec\n  - test/b.iec\n- 未実施の理由:\n')
        fields = check_pr_body.parse_sections(body)['L3']
        self.assertEqual('- test/a.iec\n- test/b.iec', fields['実行したテストファイル'])
        self.assertEqual([], check_pr_body.check_section('L3', fields))

    def test_crlf_body(self):
        body = '## L3 x\r\n\r\n- 結果: 未実施\r\n- 未実施の理由: 環境がない\r\n'
        fields = check_pr_body.parse_sections(body)['L3']
        self.assertEqual([], check_pr_body.check_section('L3', fields))


class RequiredLevelTest(unittest.TestCase):
    """Uses a temporary tree with src/ and test/ files."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.write('src/alpha/alpha.iec', _HEADER_KEYENCE)
        self.write('src/alpha/alpha_template.iec', '// no header\n')
        self.write('src/beta/beta.iec', _HEADER_OMRON)
        self.write('src/beta/beta_template.iec', '// no header\n')
        self.write('test/beta/test_beta.iec', _HEADER_OMRON)
        self.write('src/sys.iec', '// no header\n')
        self.write('test/test_sys.iec', _HEADER_KEYENCE)
        self.write('src/gamma/gamma_template.iec', '// no header\n')
        self.write('test/gamma/test_gamma.iec', _HEADER_KEYENCE)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def levels(self, *changed):
        return check_pr_body.required_levels(self.root, list(changed))

    def test_nothing_required_outside_src_and_keyence(self):
        self.assertEqual([], self.levels('README.md', 'scripts/lint.py'))
        self.assertEqual([], self.levels('test/beta/test_beta.iec'))

    def test_src_requires_l3(self):
        self.assertEqual(['L3'], self.levels('src/beta/beta.iec'))
        self.assertEqual(['L3'], self.levels('src/beta/beta_template.iec'))

    def test_keyence_header_requires_l4(self):
        self.assertEqual(['L3', 'L4'], self.levels('src/alpha/alpha.iec'))
        self.assertEqual(['L4'], self.levels('test/test_sys.iec'))

    def test_file_without_header_uses_its_module(self):
        self.assertEqual(['L3', 'L4'], self.levels('src/alpha/alpha_template.iec'))
        self.assertEqual(['L3', 'L4'], self.levels('src/gamma/gamma_template.iec'))
        self.assertEqual(['L3', 'L4'], self.levels('src/sys.iec'))

    def test_deleted_file_uses_its_module(self):
        self.assertEqual(['L3', 'L4'], self.levels('src/gamma/deleted.iec'))

    def test_check_reports_missing_records(self):
        levels, errors = check_pr_body.check(_template(), ['src/alpha/alpha.iec'], self.root)
        self.assertEqual(['L3', 'L4'], levels)
        self.assertEqual(2, len(errors), errors)


if __name__ == '__main__':
    unittest.main()
