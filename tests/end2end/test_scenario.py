import pathlib
import re

import pytest

from simplex import Program


prog_files = []
for txt in pathlib.Path().glob('*examples*/*'):
    print(txt)
    with pathlib.Path.open(txt, 'r') as f:
        raw = f.read()
    expected = {}
    for line in raw.split('\n'):
        if m := re.match(r'# expected (.*) = (.*)', line):
            expected[m.group(1)] = m.group(2)
    if expected:
        prog_files.append((txt, expected))

@pytest.mark.parametrize(('filename', 'expected'), prog_files, ids=str)
def test_prog_commands(filename, expected):
    p = Program.parse_file(filename)
    p.do_renames()
    p.do_normalize()
    if p.summary['status'] == '???':
        p.do_canonical()
    if p.summary['status'] == '???':
        p.do_standard()
    if p.summary['status'] == '???':
        p.do_tableau()
    if p.summary['status'] == '???':
        p.do_simplex()
    print('expected', expected)
    print('summary', p.summary)
    for k, v in expected.items():
        try:
            assert str(p.summary[k]) == v
        except KeyError:
            assert str(p.summary['values'][k]) == v
