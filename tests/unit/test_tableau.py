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

def test_to_tab(mock_tableau):
    expected = """x1  x2  s1  s2 |       
---------------+---=---
-1  -2   0   0 | 0 =  z
 3   0   1   0 | 4 = s1
 0   5   0   1 | 6 = s2"""
    assert mock_tableau.to_tab() == expected

def test_to_dict(mock_tableau):
    expected = """ z =  0 +  1*x1 +  2*x2
s1 =  4 + -3*x1        
s2 =  6         + -5*x2"""
    assert mock_tableau.to_dict() == expected

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
    mock_tableau.delete('x1')
    expected = """ z =  0 +  2*x2
s1 =  4        
s2 =  6 + -5*x2"""
    assert mock_tableau.to_dict() == expected
    mock_tableau.delete('x2')
    expected = """ z =  0
s1 =  4
s2 =  6"""
    assert mock_tableau.to_dict() == expected

@pytest.mark.parametrize(('candidates', 'expected'), [
    (['x1', 'x2'], {'x1': 1, 'x2': 2}),
    (['x1'], {'x1': 1}),
    (['x2'], {'x2': 2}),
])
def test_coefs_obj(mock_tableau, candidates, expected):
    assert mock_tableau.coefs_obj(candidates) == {k: -v for k, v in expected.items()}
    assert mock_tableau.coefs_obj_neg(candidates) == expected

@pytest.mark.parametrize(('col', 'expected'), [
    ('x1', {'s1': 3, 's2': 0}),
    ('x2', {'s1': 0, 's2': 5}),
])
def test_coefs_column(mock_tableau, col, expected):
    assert mock_tableau.coefs_column(col) == expected
