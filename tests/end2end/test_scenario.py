import pathlib
import re

import pytest

from simplex.__main__ import main


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
def test_main(filename, expected):
    summary = main(filename, 'bigm', 'dictionary')
    print('expected', expected)
    print('summary', summary)
    for k, v in expected.items():
        try:
            assert str(summary[k]) == v
        except KeyError:
            assert str(summary['values'][k]) == v
