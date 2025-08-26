from .expr_nodes import (
    BinaryOp,
    ExprList,
    Literal,
    Objective,
    UnaryOp,
    Variable,
)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def accept(self, *patterns):
        if token := self.current():
            for typ, value in patterns:
                if token.type == typ and (value is None or token.value == value):
                    self.pos += 1
                    return token
        return None

    def expect(self, *patterns):
        token = self.accept(*patterns)
        if token:
            return token
        msg = f'Unexpected token: expected {patterns}, got {self.current()}'
        raise SyntaxError(msg)

    def assert_end(self):
        if self.current() is not None:
            msg = f'Unexpected token(s) at end ({self.tokens[self.pos:]})'
            raise SyntaxError(msg)

    def assert_not_end(self):
        if self.current() is None:
            msg = 'Unexpected end of input'
            raise SyntaxError(msg)

    def parse(self):
        if token := self.accept(('OP', 'min'), ('OP', 'max')):
            expr_left = self.parse_logic()
            self.expect(('OP', '='))
            expr_right = self.parse_logic()
            return Objective(token.value, expr_left, expr_right)

        if expr := self.parse_logic():
            return expr

        msg = f'Unable to parse expression: {self.tokens}'
        raise SyntaxError(msg)

    def parse_logic(self):
        self.assert_not_end()

        expr_left = self.parse_comparison()
        while token := self.accept(
                    ('OP', 'and'),
                    ('OP', 'or'),
                    ('OP', 'xor'),
                    ('OP', 'if'),
                    ('OP', 'iif'),
        ):
            expr_left = BinaryOp(token.value, expr_left, self.parse_comparison())
        return expr_left

    def parse_comparison(self):
        self.assert_not_end()

        expr_left = self.parse_low()
        while token := self.accept(
                    ('OP', '<='),
                    ('OP', '<'),
                    ('OP', '=='),
                    ('OP', '!='),
                    ('OP', '>'),
                    ('OP', '>='),
        ):
            expr_left = BinaryOp(token.value, expr_left, self.parse_low())
        return expr_left

    def parse_low(self):
        self.assert_not_end()

        expr_left = self.parse_high()
        while token := self.accept(
                    ('OP', '+'),
                    ('OP', '-'),
        ):
            expr_left = BinaryOp(token.value, expr_left, self.parse_high())
        return expr_left

    def parse_high(self):
        self.assert_not_end()

        expr_left = self.parse_atom()
        while token := self.accept(
                ('OP', '*'),
                ('OP', '/'),
        ):
            expr_left = BinaryOp(token.value, expr_left, self.parse_atom())
        return expr_left

    def parse_atom(self):
        self.assert_not_end()

        if token := self.accept(
                ('OP', 'not'),
                ('OP', '-'),
        ):
            return UnaryOp(token.value, self.parse_atom())
        if token := self.accept(
                ('BOOL', None),
                ('NUMBER', None),
        ):
            return Literal(token.value)
        if token := self.accept(('VAR', None)):
            tmp = []
            while self.accept(('COMMA', ',')):
                tmp.append(Variable(self.expect(('VAR', None)).value))
            if tmp:
                return ExprList([Variable(token.value), *tmp])
            return Variable(token.value)
        if token := self.accept(('LPAREN', None)):
            expr = self.parse_logic()
            tmp = []
            while self.accept(('COMMA', ',')):
                tmp.append(self.parse_logic())
            self.expect(('RPAREN', None))
            if tmp:
                return ExprList([expr, *tmp])
            return expr

        msg = f'Unexpected token {self.current()}'
        raise SyntaxError(msg)
