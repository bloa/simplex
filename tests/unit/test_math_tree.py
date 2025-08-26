import pytest

from simplex import BoolTree, ExprTree, MathTree, ObjectiveTree


## Typing errors

@pytest.mark.parametrize(('expr', 'expected'), [
    ('not 1', TypeError),
    ('1 and 2', TypeError),
    ('1 and (x + y)', TypeError),
    ('1 + (x or y)', TypeError),
    ('1 + (!x)', TypeError),
])
def test_expr_tree_typing_error(expr, expected):
    with pytest.raises(expected):
        ExprTree.from_string(expr)

@pytest.mark.parametrize(('expr', 'expected'), [
    ('not x', TypeError),
    ('x < y', TypeError),
    ('x and y', TypeError),
])
def test_math_tree_typing_error(expr, expected):
    with pytest.raises(expected):
        print(MathTree.from_string(expr))

@pytest.mark.parametrize(('expr', 'expected'), [
    ('1', TypeError),
    ('x + y', TypeError),
])
def test_bool_tree_typing_error(expr, expected):
    with pytest.raises(expected):
        BoolTree.from_string(expr)

@pytest.mark.parametrize(('expr', 'expected'), [
    ('1 + 2', TypeError),
    ('min', SyntaxError),
    ('max x', SyntaxError),
    ('max x = x', SyntaxError),
    ('max 2*x = y', SyntaxError),
])
def test_objective_tree_typing_error(expr, expected):
    with pytest.raises(expected):
        ObjectiveTree.from_string(expr)


## Runtime

@pytest.mark.parametrize(('expr', 'context', 'expected'), [
    ('1 + 2', {}, 3),
    ('-1 + 2', {}, 1),
    ('-(-1)', {}, 1),
    ('-(((-(-(1)))))', {}, -1),
    ('1.2 + 2.5', {}, 3.7),
    ('(2 + x) * y', {'x': 2, 'y': 3}, 12),
    ('2 + x * y', {'x': 2, 'y': 3}, 8),
    ('foo < 0 or foo >= 10', {'foo': -1}, True),
    ('foo < 0 or foo >= 10', {'foo': 0}, False),
    ('foo < 0 or foo >= 10', {'foo': 4}, False),
    ('foo < 0 or foo >= 10', {'foo': 10}, True),
    ('foo < 0 or foo >= 10', {'foo': 11}, True),
    ('x < y', {'x': 1, 'y': 3}, True),
    ('x < y', {'x': 4, 'y': 3}, False),
    ('x == 1', {'x': 1}, True),
    ('x == 2', {'x': 1}, False),
    ('x1, x2 > 0', {'x1': 1, 'x2': 2}, True),
    ('x1, x2 > 0', {'x1': 0, 'x2': 2}, False),
])
def test_expr_tree_runtime(expr, context, expected):
    assert ExprTree.from_string(expr).evaluate(context) == expected

@pytest.mark.parametrize(('expr', 'context', 'expected'), [
    ('min x = 1 + 2', {}, 3),
    ('min x = -1 + 2', {}, 1),
    ('min x = -(-1)', {}, 1),
    ('min x = -(((-(-(1)))))', {}, -1),
    ('max z = 1.2 + 2.5', {}, 3.7),
    ('max z = (2 + x) * 3', {'x': 2}, 12),
    ('max z = 2 + 2 * y', {'y': 3}, 8),
])
def test_objective_tree_runtime(expr, context, expected):
    assert ObjectiveTree.from_string(expr).evaluate(context) == expected


## Runtime errors

@pytest.mark.parametrize(('expr', 'context', 'expected'), [
    ('x < y', {'x': 1}, KeyError),
    ('x < y', {'x': 1, 'y': 'foo'}, TypeError),
    ('x < y', {'x': 1, 'y': None}, TypeError),
    ('x + y', {'x': 1, 'y': None}, TypeError),
])
def test_expr_tree_runtime_error(expr, context, expected):
    with pytest.raises(expected):
        ExprTree.from_string(expr).evaluate(context)


## Simplify

@pytest.mark.parametrize(('expr', 'expected'), [
    # simplify
    ('-5', '-5'),
    ('--5', '5'),
    ('---5', '-5'),
    ('1+2+3', '6'),
    ('x - (-1)', 'x + 1'),
    ('(2*x)*7', '14*x'),
    # distribute
    ('-(1*x + 3*y)', '-x + -3*y'),
    ('1*(1 + ((2 + (x*3)) + (2 * (y + 1) * 1))*2)', '6*x + 4*y + 9'),
    ('((2*x1) + ((x2*3) + x1)) - (2 + ((3 - 4) - 5))', '3*x1 + 3*x2 + 4'),
    ('1 < x', '-x <= -1'),
    ('x < 0', 'x <= 0'),
    ('-x < 0', 'x >= 0'),
    ('2*x1 + 2*x2 - 11 <= 0', '2*x1 + 2*x2 <= 11'),
    (' 2*x1 - 11 <= - 2*x2', '2*x1 + 2*x2 <= 11'),
    ('x1 + x4 >= -5', '-x1 + -x4 <= 5'),
    ('x + 2*y >= 0', '-x + -2*y <= 0'),
    # negate
    ('not(not x)', 'x'),
    ('not(x < 0)', 'x >= 0'),
    ('not(x > 0)', 'x <= 0'),
    ('not(x <= 0)', 'x >= 0'),
    ('not(x >= 0)', 'x <= 0'),
    ('not(x == 0)', '(x >= 0) or (x <= 0)'),
    ('not(x != 0)', '(x >= 0) and (x <= 0)'),
    # reduce
    ('x + 1 + x', '2*x + 1'),
    ('x + 1 + 2*x', '3*x + 1'),
    ('2*x + 1 + x', '3*x + 1'),
    ('2*x + 1 + 3*x', '5*x + 1'),
    ('x + y + x', '2*x + y'),
    ('x + y + y', 'x + 2*y'),
    ('x + y + z + 1 + z + y + x', '2*x + 2*y + 2*z + 1'),
    ('x + y + z + 1 + z + y + x + z + y + x', '3*x + 3*y + 3*z + 1'),
    ('(x + y + z + 1 + 2*z + 2*y + 2*x) + z + y + x', '4*x + 4*y + 4*z + 1'),
    # Booleans
    ('not True', 'False'),
    ('not False', 'True'),
    ('not x or y', '(not x) or y'),
    ('not (x or y)', '(not x) and (not y)'),
    ('not (x or not y)', '(not x) and y'),
    ('not (x and y)', '(not x) or (not y)'),
    ('not (x and not y)', '(not x) or y'),
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
    ('x if y', 'x or (not y)'),
    ('x iif y', '(x or (not y)) and (y or (not x))'),
    ('max z = 0 + 1', 'max z = 1'),
    ('max -z = -x', 'max -z = -x'),
    ('max 2*z = -x', 'max z = -1/2*x'),
    ('max 1/2*z = -x', 'max z = -2*x'),
])
def test_expr_simplify(expr, expected):
    tree = ExprTree.from_string(expr)
    print(str(tree))
    tree.normalize()
    print(str(tree))
    assert str(tree) == expected
