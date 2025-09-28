import itertools
import pathlib
import re

import pytest

from simplex.__main__ import main


prog_files = []
expected_files = {}
for path in pathlib.Path().glob('*examples*/*'):
    prog_files.append(path)
    with pathlib.Path.open(path, 'r') as f:
        raw = f.read()
    expected = {}
    for line in raw.split('\n'):
        if m := re.match(r'# expected (.*) = (.*)', line):
            expected[m.group(1)] = m.group(2)
    if expected:
        expected_files[path] = expected

solvers = ['bigm', 'twophase']
methods = ['dictionary', 'tableau', 'compact', 'tableau_alt', 'compact_alt']
latexs = [True, False]

tmp = itertools.product(prog_files, solvers, methods, latexs)
@pytest.mark.parametrize(('filename', 'solver', 'method', 'latex'), tmp, ids=str)
def test_main(filename, solver, method, latex):
    summary = main(filename, solver, method, latex, 3628800)
    if filename in expected_files:
        expected = expected_files[filename]
        print('expected', expected)
        print('summary', summary)
        for k, v in expected.items():
            try:
                assert str(summary[k]) == v
            except KeyError:
                assert str(summary['values'][k]) == v
    else:
        expected_files[filename] = {'status': summary['status']}
