import pytest

from simplex.expr_trees import tokenize


def tokens_of(s):
    return [(t.type, t.value) for t in tokenize(s)]

@pytest.mark.parametrize(('expr', 'expected'), [
    ('2 + x * 3', [
        ('NUMBER', 2),
        ('OP', '+'),
        ('VAR', 'x'),
        ('OP', '*'),
        ('NUMBER', 3),
    ]),
    ('x * 2 < 10 and y == 1', [
        ('VAR', 'x'),
        ('OP', '*'),
        ('NUMBER', 2),
        ('OP', '<'),
        ('NUMBER', 10),
        ('OP', 'and'),
        ('VAR', 'y'),
        ('OP', '=='),
        ('NUMBER', 1),
    ]),
    ('!x', [
        ('OP', 'not'),
        ('VAR', 'x'),
    ]),
    ('-(-x)', [
        ('OP', '-'),
        ('LPAREN', '('),
        ('OP', '-'),
        ('VAR', 'x'),
        ('RPAREN', ')'),
    ]),
    ('!(2 * x < 10 or y == 1)', [
        ('OP', 'not'),
        ('LPAREN', '('),
        ('NUMBER', 2),
        ('OP', '*'),
        ('VAR', 'x'),
        ('OP', '<'),
        ('NUMBER', 10),
        ('OP', 'or'),
        ('VAR', 'y'),
        ('OP', '=='),
        ('NUMBER', 1),
        ('RPAREN', ')'),
    ]),
    ('max z = 2*x - y', [
        ('OP', 'max'),
        ('VAR', 'z'),
        ('OP', '='),
        ('NUMBER', 2),
        ('OP', '*'),
        ('VAR', 'x'),
        ('OP', '-'),
        ('VAR', 'y'),
    ]),
    ('x1, x2 > 0', [
        ('VAR', 'x1'),
        ('COMMA', ','),
        ('VAR', 'x2'),
        ('OP', '>'),
        ('NUMBER', 0),
    ]),
    ('1*x + 2y + 3', [
        ('NUMBER', 1),
        ('OP', '*'),
        ('VAR', 'x'),
        ('OP', '+'),
        ('NUMBER', 2),
        ('VAR', 'y'),
        ('OP', '+'),
        ('NUMBER', 3),
    ]),
])
def test_tokenize(expr, expected):
    assert tokens_of(expr) == expected

@pytest.mark.parametrize(('expr', 'expected'), [
    ('-foo', [
        ('OP', '-'),
        ('VAR', 'foo'),
    ]),
    ('foo-1', [
        ('VAR', 'foo'),
        ('OP', '-'),
        ('NUMBER', 1),
    ]),
    ('foo - 1', [
        ('VAR', 'foo'),
        ('OP', '-'),
        ('NUMBER', 1),
    ]),
    ('foo--', [
        ('VAR', 'foo'),
        ('OP', '-'),
        ('OP', '-'),
    ]),
    ('foo- - 1', [
        ('VAR', 'foo'),
        ('OP', '-'),
        ('OP', '-'),
        ('NUMBER', 1),
    ]),
])
def test_tokenize_hypens(expr, expected):
    assert tokens_of(expr) == expected

