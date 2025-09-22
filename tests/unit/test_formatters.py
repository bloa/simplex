import pytest

from simplex.core import Tableau
from simplex.parsing import ExprTree, ObjectiveTree
from simplex.formatters import DictCliFormatter, TableauCliFormatter

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
    formatter = TableauCliFormatter()
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_dict(mock_tableau):
    expected = """ z =  0 +  1*x1 +  2*x2
s1 =  4 + -3*x1        
s2 =  6         + -5*x2"""
    formatter = DictCliFormatter()
    assert formatter.format_tableau(mock_tableau) == expected
