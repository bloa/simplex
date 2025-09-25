import pathlib
import re

import pytest

from simplex.__main__ import main


prog_files = []
solvers = ['bigm']
methods = ['dictionary', 'tableau', 'compact']
latex = [True, False]
for k, txt in enumerate(pathlib.Path().glob('*examples*/*')):
    print(txt)
    with pathlib.Path.open(txt, 'r') as f:
        raw = f.read()
    expected = {}
    for line in raw.split('\n'):
        if m := re.match(r'# expected (.*) = (.*)', line):
            expected[m.group(1)] = m.group(2)
    if expected:
        prog_files.append((txt, expected, solvers[k%len(solvers)], methods[k%len(methods)], latex[k%len(latex)]))

@pytest.mark.parametrize(('filename', 'expected', 'solver', 'method', 'latex'), prog_files, ids=str)
def test_main(filename, expected, solver, method, latex):
    summary = main(filename, solver, method, latex)
    print('expected', expected)
    print('summary', summary)
    for k, v in expected.items():
        try:
            assert str(summary[k]) == v
        except KeyError:
            assert str(summary['values'][k]) == v
