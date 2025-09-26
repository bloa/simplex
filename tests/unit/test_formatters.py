import pytest

from simplex.core import Model, Tableau
from simplex.parsing import ExprTree, ObjectiveTree
from simplex.formatters import DictCliFormatter, TableauCliFormatter, DictLatexFormatter, TableauLatexFormatter


@pytest.fixture
def mock_model():
    return Model.parse_str("""
max z = x1 + 2*x2
3*x1 <= 4
5*x2 <= 6
x1 >= 0
x2 >= 0
""")

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

def test_model(mock_model):
    expected = """    max z = x1 + 2*x2
    3*x1 <= 4
    5*x2 <= 6
    x1, x2 >= 0"""
    formatter = TableauCliFormatter()
    assert formatter.format_model(mock_model) == expected

def test_to_tab(mock_tableau):
    expected = """    x1  x2  s1  s2 |        
    ---------------+----=---
     3   0   1   0 |  4 = s1
     0   5   0   1 |  6 = s2
    ---------------+----=---
     1   2   0   0 |  0 = -z"""
    formatter = TableauCliFormatter()
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_compact(mock_tableau):
    expected = """    x1  x2 |        
    -------+----=---
     3   0 |  4 = s1
     0   5 |  6 = s2
    -------+----=---
     1   2 |  0 = -z"""
    formatter = TableauCliFormatter()
    formatter.compact = True
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_tab_alt(mock_tableau):
    expected = """    x1  x2  s1  s2 |        
    ---------------+----=---
    -1  -2   0   0 |  0 =  z
     3   0   1   0 |  4 = s1
     0   5   0   1 |  6 = s2"""
    formatter = TableauCliFormatter()
    formatter.opposite_obj = False
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_compact_alt(mock_tableau):
    expected = """    x1  x2 |        
    -------+----=---
    -1  -2 |  0 =  z
     3   0 |  4 = s1
     0   5 |  6 = s2"""
    formatter = TableauCliFormatter()
    formatter.compact = True
    formatter.opposite_obj = False
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_dict(mock_tableau):
    expected = """     z =  0 +  1*x1 +  2*x2
    s1 =  4 + -3*x1        
    s2 =  6         + -5*x2"""
    formatter = DictCliFormatter()
    assert formatter.format_tableau(mock_tableau) == expected

def test_latex_model(mock_model):
    expected = r"""\begin{equation*}
  \arraycolsep=0.3em
  \begin{array}{rrcrcr}
    \text{maximise} & z = x_1 & + & 2x_2\\
    \text{subject to} & 3x_1 &  &  & \leq & 4\\
    &  &  & 5x_2 & \leq & 6\\
    & \multicolumn{3}{r}{x_1, x_2} & \geq & 0\\
  \end{array}
\end{equation*}"""
    formatter = TableauLatexFormatter()
    assert formatter.format_model(mock_model) == expected

def test_to_latex_tab(mock_tableau):
    expected = r"""\begin{equation*}
  \begin{array}{rrrr|rcr}
    x1 & x2 & s1 & s2\\
    \hline
     3 &  0 &  1 &  0 &  4 & = & s1\\
     0 &  5 &  0 &  1 &  6 & = & s2\\
    \hline
     1 &  2 &  0 &  0 &  0 & = & -z\\
  \end{array}
\end{equation*}"""
    formatter = TableauLatexFormatter()
    formatter.opposite_obj = True
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_latex_compact(mock_tableau):
    expected = r"""\begin{equation*}
  \begin{array}{rr|rcr}
    x1 & x2\\
    \hline
     3 &  0 &  4 & = & s1\\
     0 &  5 &  6 & = & s2\\
    \hline
     1 &  2 &  0 & = & -z\\
  \end{array}
\end{equation*}"""
    formatter = TableauLatexFormatter()
    formatter.compact = True
    formatter.opposite_obj = True
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_latex_tab_alt(mock_tableau):
    expected = r"""\begin{equation*}
  \begin{array}{rrrr|rcr}
    x1 & x2 & s1 & s2\\
    \hline
    -1 & -2 &  0 &  0 &  0 & = &  z\\
     3 &  0 &  1 &  0 &  4 & = & s1\\
     0 &  5 &  0 &  1 &  6 & = & s2\\
  \end{array}
\end{equation*}"""
    formatter = TableauLatexFormatter()
    formatter.opposite_obj = False
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_latex_compact_alt(mock_tableau):
    expected = r"""\begin{equation*}
  \begin{array}{rr|rcr}
    x1 & x2\\
    \hline
    -1 & -2 &  0 & = &  z\\
     3 &  0 &  4 & = & s1\\
     0 &  5 &  6 & = & s2\\
  \end{array}
\end{equation*}"""
    formatter = TableauLatexFormatter()
    formatter.compact = True
    formatter.opposite_obj = False
    assert formatter.format_tableau(mock_tableau) == expected

def test_to_latex_dict(mock_tableau):
    expected = r"""\begin{equation*}
  \begin{array}{|rcrcrcr|}
    \hline
     z & = &  0 & + &  1x_1 & + &  2x_2\\
    \hline
    s1 & = &  4 & + & -3x_1 &   &      \\
    s2 & = &  6 &   &       & + & -5x_2\\
    \hline
  \end{array}
\end{equation*}"""
    formatter = DictLatexFormatter()
    assert formatter.format_tableau(mock_tableau) == expected
