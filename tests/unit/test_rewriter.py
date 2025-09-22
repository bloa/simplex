import pytest

from simplex.core import Rewriter
from simplex.parsing import ExprTree


@pytest.mark.parametrize(('expr', 'expected'), [
    ## MATH
    # literals
    ('1.0', '1'),
    ('1.5', '3/2'),
    ('2/4', '1/2'),
    ('4/4', '1'),
    # unary -
    ('-5', '-5'),
    ('--5', '5'),
    ('---5', '-5'),
    ('x - (-1)', 'x + 1'),
    # reduction
    ('1+2+3', '6'),
    ('(2*x)*7', '14*x'),
    ('x + 1 + x', '2*x + 1'),
    ('x + 1 + 2*x', '3*x + 1'),
    ('2*x + 1 + x', '3*x + 1'),
    ('2*x + 1 + 3*x', '5*x + 1'),
    ('x + y + x', '2*x + y'),
    ('x + y + y', 'x + 2*y'),
    ('x + y + z + 1 + z + y + x', '2*x + 2*y + 2*z + 1'),
    ('x + y + z + 1 + z + y + x + z + y + x', '3*x + 3*y + 3*z + 1'),
    ('(x + y + z + 1 + 2*z + 2*y + 2*x) + z + y + x', '4*x + 4*y + 4*z + 1'),
    ('-(1*x + 3*y)', '-x + -3*y'),
    ('1*(1 + ((2 + (x*3)) + (2 * (y + 1) * 1))*2)', '6*x + 4*y + 9'),
    ('((2*x1) + ((x2*3) + x1)) - (2 + ((3 - 4) - 5))', '3*x1 + 3*x2 + 4'),
    ## LOGIC
    # negation
    ('not(not x)', 'x'),
    ('not(x < 0)', 'x >= 0'),
    ('not(x > 0)', 'x <= 0'),
    ('not(x <= 0)', 'x >= 0'),
    ('not(x >= 0)', 'x <= 0'),
    ('not(x == 0)', 'x != 0'),
    ('not(x != 0)', 'x == 0'),
    ('not True', 'False'),
    ('not False', 'True'),
    ('not x or y', '(not x) or y'),
    ('x or not y', 'x or (not y)'),
    ('not x or not y', '(not x) or (not y)'),
    ('not (x or y)', '(not x) and (not y)'),
    ('not (x or not y)', '(not x) and y'),
    ('not (x and y)', '(not x) or (not y)'),
    ('not (x and not y)', '(not x) or y'),
    # reduction
    ('x and x', 'x'),
    ('x or x', 'x'),
    ('x or not x', 'True'),
    ('x or y or not x', 'True'),
    ('x xor y', '(x or y) and ((not x) or (not y))'),
    ('x xor not y', '(x or (not y)) and ((not x) or y)'),
    ('x xor not x', 'True'),
    ('x and y and x', 'x and y'),
    ('x and y and not x', 'False'),
    ('x and True', 'x'),
    ('x or True', 'True'),
    ('True xor x', 'not x'),
    # rewriting
    ('x if y', 'x or (not y)'),
    ('x iif y', '(x or (not y)) and (y or (not x))'),
    ## COMPARISONS
    ('x < 1', 'x <= 1'),
    ('1 < x', '-x <= -1'),
    ('-x > 0', 'x <= 0'),
    ('-x < 0', 'x >= 0'),
    ('2*x1 + 2*x2 - 11 <= 0', '2*x1 + 2*x2 <= 11'),
    ('2*x1 - 11 <= - 2*x2', '2*x1 + 2*x2 <= 11'),
    ('1 == 1', 'True'),
    ('1 == 2', 'False'),
    ('1 < 1', 'False'), # dubious
    ('1 <= 1', 'True'),
    ('1 <= 2', 'True'),
    ('1 >= 2', 'False'),
    # OBJECTIVES
    ('max z = 0 + 1', 'max z = 1'),
    ('max -z = -x', 'max -z = -x'),
    ('max 2*z = -x', 'max z = -1/2*x'),
    ('max 1/2*z = -x', 'max z = -2*x'),
    # LISTS
    ('x, y >= 0', 'x >= 0, y >= 0'),
])
def test_expr_normalize(expr, expected):
    tree = ExprTree.from_string(expr)
    print(str(tree))
    Rewriter().normalize(tree)
    print(str(tree))
    assert str(tree) == expected
