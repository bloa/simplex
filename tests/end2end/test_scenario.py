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
from_duals = [True, False]
to_duals = [True, False]
methods = ['dictionary', 'tableau', 'compact', 'tableau_alt', 'compact_alt']
latexs = [True, False]
m = 3628800

tmp = itertools.product(prog_files, solvers, from_duals, to_duals, methods, latexs)
@pytest.mark.parametrize(('filename', 'solver', 'from_dual', 'to_dual', 'method', 'latex'), tmp, ids=str)
def test_main(filename, solver, from_dual, to_dual, method, latex):
    summary = main(filename, solver, from_dual, to_dual, method, latex, m)
    if filename in expected_files:
        expected = expected_files[filename]
        print('expected', expected)
        print('summary', summary)
        for k, v in expected.items():
            if from_dual == to_dual:
                if k in ['status', 'objective']:
                    assert str(summary[k]) == v
                elif not (from_dual or to_dual):
                    assert str(summary['values'][k]) == v
            elif k == 'status':
                if v == 'SOLVED':
                    assert str(summary[k]) == 'SOLVED'
                elif v == 'UNBOUNDED':
                    assert str(summary[k]) == 'INFEASIBLE'
                elif v == 'INFEASIBLE':
                    assert str(summary[k]) == 'UNBOUNDED'
    else:
        expected_files[filename] = {'status': summary['status']}
        if 'objective' in summary:
            expected_files[filename]['objective'] = summary['objective']
