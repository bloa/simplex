import pytest

from simplex.core import Rewriter, Tableau
from simplex.parsing import ExprTree, MathTree, ObjectiveTree


@pytest.fixture
def mock_tableau():
    objective = ObjectiveTree.from_string('max z = x1 + 2*x2')
    constraints = [ExprTree.from_string(s) for s in [
        '3*x1 + s1 == 4',
        '5*x2 + s2 == 6',
        'x1 >= 0',
        'x2 >= 0',
        's1 >= 0',
        's2 >= 0',
    ]]
    initial_basis = ['s1', 's2']
    return Tableau(objective, constraints, initial_basis)

@pytest.mark.parametrize(('expr', 'expected'), [
    ('x1 + x2 + x3', {'x1': 1, 'x2': 1, 'x3': 1, '': 0}),
    ('x + 2*y + x', {'x': 2, 'y': 2, '': 0}),
    ('1', {'': 1}),
    ('2*x - 1', {'x': 2, '': -1}),
])
def test_aux_data(expr, expected):
    tree = MathTree.from_string(expr)
    Rewriter().normalize(tree)
    tmp = Tableau.aux_data(tree.root, [*tree.variables, ''])
    assert {k: str(v) for k, v in tmp.items()} == {k: str(v) for k, v in expected.items()}


def test_delete(mock_tableau):
    assert 'x1' in mock_tableau.columns
    assert 'x2' in mock_tableau.columns
    mock_tableau.delete('x1')
    assert 'x1' not in mock_tableau.columns
    assert 'x2' in mock_tableau.columns
    mock_tableau.delete('x2')
    assert 'x1' not in mock_tableau.columns
    assert 'x2' not in mock_tableau.columns

@pytest.mark.parametrize(('candidates', 'expected'), [
    (['x1', 'x2'], {'x1': 1, 'x2': 2}),
    (['x1'], {'x1': 1}),
    (['x2'], {'x2': 2}),
])
def test_coefs_obj(mock_tableau, candidates, expected):
    tmp = mock_tableau.coefs_obj(candidates)
    assert {k: -v.evaluate({}) for k,v in tmp.items()} == expected

@pytest.mark.parametrize(('col', 'expected'), [
    ('s1', {'x1': 3, 'x2': 0, 's1': 1, 's2': 0, '': 4}),
    ('s2', {'x1': 0, 'x2': 5, 's1': 0, 's2': 1, '': 6}),
])
def test_coefs_row(mock_tableau, col, expected):
    tmp = mock_tableau.coefs_row(col)
    assert {k: v.evaluate({}) for k,v in tmp.items()} == expected

@pytest.mark.parametrize(('col', 'expected'), [
    ('x1', {'s1': 3, 's2': 0}),
    ('x2', {'s1': 0, 's2': 5}),
])
def test_coefs_column(mock_tableau, col, expected):
    tmp = mock_tableau.coefs_column(col)
    assert {k: v.evaluate({}) for k,v in tmp.items()} == expected
