import pytest

from simplex.parsing import BoolTree, ExprTree, MathTree, ObjectiveTree


## Syntax errors

@pytest.mark.parametrize(('expr', 'expected'), [
    ('not', SyntaxError),
    ('1 and', SyntaxError),
    ('x y', SyntaxError),
    ('+ 2', SyntaxError),
])
def test_expr_tree_syntax_error(expr, expected):
    with pytest.raises(expected):
        ExprTree.from_string(expr)


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
        MathTree.from_string(expr)

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
    ('2*x', {'x':3}, 6),
    ('2x', {'x':3}, 6),
    ('2 x1', {'x1':3}, 6),
    ('2x * y', {'x':3, 'y':5}, 30),
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
