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
    prog_files.append((txt, expected))

main_params = []
for (txt, expected) in prog_files:
    for solver in ['bigm', 'twophase']:
        for method in ['dictionary', 'tableau', 'compact', 'tableau_alt', 'compact_alt']:
            for latex in [True, False]:
                main_params.append((txt, expected, solver, method, latex))

@pytest.mark.parametrize(('filename', 'expected', 'solver', 'method', 'latex'), main_params, ids=str)
def test_main(filename, expected, solver, method, latex):
    summary = main(filename, solver, method, latex)
    if expected:
        print('expected', expected)
        print('summary', summary)
        for k, v in expected.items():
            try:
                assert str(summary[k]) == v
            except KeyError:
                assert str(summary['values'][k]) == v
