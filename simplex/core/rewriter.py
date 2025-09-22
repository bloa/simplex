import math

from simplex.parsing import (
    BinaryOp,
    ExprList,
    Literal,
    Objective,
    UnaryOp,
    Variable,
)


class Rewriter:
    def __init__(self):
        self.variables = None

    @classmethod
    def _almost_literal(cls, node):
        if isinstance(node, Literal):
            return True
        if isinstance(node, UnaryOp):
            return cls._almost_literal(node.right)
        if isinstance(node, BinaryOp):
            return cls._almost_literal(node.left) and cls._almost_literal(node.right)
        return False

    @classmethod
    def _almost_variable(cls, node, single=False):
        if isinstance(node, ExprList):
            return all(cls._almost_variable(e) for e in node.exprlist)
        if isinstance(node, Variable):
            return True
        if isinstance(node, UnaryOp):
            return cls._almost_variable(node.right)
        if isinstance(node, BinaryOp) and (single or node.op == '*'):
            return cls._almost_literal(node.left) and cls._almost_variable(node.right)
        return False

    @staticmethod
    def _is_unaop(expr, op):
        return isinstance(expr, UnaryOp) and expr.op == op

    @staticmethod
    def _is_binop(expr, op):
        return isinstance(expr, BinaryOp) and expr.op == op

    @classmethod
    def _nominators(cls, node, acc):
        if isinstance(node, Literal):
            return acc | {node.value}
        if isinstance(node, Variable):
            return acc | {1}
        if isinstance(node, ExprList):
            return acc | {1}
        if isinstance(node, BinaryOp) and node.op in {'+', '-'}:
            return cls._nominators(node.right, cls._nominators(node.left, acc))
        if isinstance(node, BinaryOp) and node.op == '*':
            return cls._nominators(node.left, acc)
        return acc

    @classmethod
    def _denominators(cls, node, acc):
        if cls._is_binop(node, '/'):
            return acc | cls._nominators(node.right, set())
        if isinstance(node, UnaryOp):
            return cls._denominators(node.right, acc)
        if isinstance(node, BinaryOp) and node.op in {'+', '-', '*'}:
            return cls._denominators(node.right, cls._denominators(node.left, acc))
        return acc

    def _is_unsorted(self, left, right):
        return self.variables.index(left) > self.variables.index(right)

    def _normalize_visitor(self, node):
        def unaop(op, right):
            return self._normalize_visitor(UnaryOp(op, right))
        def binop(op, left, right):
            return self._normalize_visitor(BinaryOp(op, left, right))

        match node:
            case Literal():
                if '.' in str(node.value):
                    i = int(node.value)
                    f = node.value - i
                    n = len(str(f)) - 2
                    if f == 0:
                        return Literal(i)
                    return binop('/', Literal(int(10**n*node.value)), Literal(10**n))

            case Objective():
                if isinstance(node.var, BinaryOp):
                    if isinstance(node.var.left, Literal):
                        if node.var.left.value > 0:
                            return Objective(node.mode, node.var.right, binop('/', node.right, node.var.left))
                        if node.var.left.value != -1:
                            return Objective(node.mode, unaop('-', node.var.right), binop('/', node.right, node.var.left))
                    elif self._is_binop(node.var.left, '/'):
                        if node.var.left.left.value > 0:
                            return Objective(node.mode, node.var.right, binop('*', binop('/', node.var.left.right, node.var.left.left), node.right))
                        if node.var.left.left.value != -1:
                            return Objective(node.mode, unaop('-', node.var.right), binop('*', binop('/', node.var.left.right, node.var.left.left), node.right))

            case UnaryOp():
                # rewrite expression lists
                if isinstance(node.right, ExprList):
                    return ExprList([unaop(node.op, e) for e in node.right.exprlist])
                # rewrite unary "-"
                if node.op == '-':
                    if isinstance(node.right, Literal):
                        return Literal(-node.right.value)
                    if isinstance(node.right, Variable):
                        return binop('*', Literal(-1), node.right)
                    if isinstance(node.right, UnaryOp) and node.right.op == '-':
                        return node.right.right
                    if isinstance(node.right, BinaryOp):
                        if node.right.op in ('*', '/'):
                            return binop(node.right.op, unaop(node.op, node.right.left), node.right.right)
                        if node.right.op in ('+', '-'):
                            return binop(node.right.op, unaop(node.op, node.right.left), unaop(node.op, node.right.right))
                # simplify and distribute "not"
                if node.op == 'not':
                    if str(node.right) == 'True':
                        return Literal(False)
                    if str(node.right) == 'False':
                        return Literal(True)
                    if isinstance(node.right, UnaryOp) and node.right.op == 'not':
                        return node.right.right
                    if isinstance(node.right, BinaryOp):
                        if node.right.op == 'or':
                            return binop('and', unaop('not', node.right.left), unaop('not', node.right.right))
                        if node.right.op == 'and':
                            return binop('or', unaop('not', node.right.left), unaop('not', node.right.right))
                        h = {'>': '<=', '<': '>=', '>=': '<', '<=': '>', '==': '!=', '!=': '=='}
                        return binop(h[node.right.op], node.right.left, node.right.right)

            case BinaryOp():
                # rewrite expression lists
                if isinstance(node.left, ExprList):
                    return ExprList([binop(node.op, e, node.right) for e in node.left.exprlist])
                if isinstance(node.right, ExprList):
                    return ExprList([binop(node.op, node.left, e) for e in node.right.exprlist])
                # rewrite binary "-"
                if node.op == '-':
                    return binop('+', node.left, unaop('-', node.right))
                if node.op == '*':
                    # simplify "*0" to avoid inf*0
                    if isinstance(node.right, Literal) and node.right.value == 0:
                        return node.right
                    # simplify "0*"
                    if isinstance(node.left, Literal) and node.left.value == 0:
                        return node.left
                    # simplify "1*"
                    if isinstance(node.left, Literal) and node.left.value == 1:
                        return node.right
                    # reduce literals ; move literals left
                    if isinstance(node.right, Literal):
                        if isinstance(node.left, Literal):
                            return Literal(node.left.value * node.right.value)
                        return binop('*', node.right, node.left)
                    # distribute "*" inside "+"; reduce stacks of "*"
                    if isinstance(node.left, Literal):
                        if self._is_binop(node.right, '+'):
                            return binop('+', binop('*', node.left, node.right.left), binop('*', node.left, node.right.right))
                        if self._is_binop(node.right, '*'):
                            return binop('*', binop('*', node.left, node.right.left), node.right.right)
                    # distribute "*" inside "/"
                    if isinstance(node.right, BinaryOp) and node.right.op == '/':
                            return binop('/', binop('*', node.left, node.right.left), node.right.right)
                if node.op == '/':
                    # move variables outside divisions
                    if isinstance(node.left, Variable):
                        return binop('*', binop('/', Literal(1), node.right), node.left)
                    if self._is_binop(node.left, '*'):
                        return binop('*', binop('/', node.left.left, node.right), node.left.right)
                    if self._is_binop(node.left, '+'):
                        return binop('+', binop('/', node.left.left, node.right), binop('/', node.left.right, node.right))
                    # simplify literal fractions
                    if isinstance(node.left, Literal) and isinstance(node.right, Literal):
                        if abs(node.left.value) == float('inf'):
                            return node.left
                        if node.right.value == 1:
                            return node.left
                        if node.left.value == node.right.value:
                            return Literal(1)
                        if node.right.value < 0:
                            return binop('/', Literal(-node.left.value), Literal(-node.right.value))
                        gcd = math.gcd(node.left.value, node.right.value)
                        if gcd != 1:
                            return binop('/', Literal(node.left.value//gcd), Literal(node.right.value//gcd))
                    # unify fractions
                    if self._is_binop(node.left, '/'):
                        return binop('/', node.left.left, binop('*', node.left.right, node.right))
                    if self._is_binop(node.right, '/'):
                        return binop('/', binop('*', node.left, node.right.right), node.right.left)
                if node.op == '+':
                    # linearize "+" trees
                    if self._is_binop(node.right, '+'):
                        return binop('+', binop('+', node.left, node.right.left), node.right.right)
                    # reduce literals
                    if isinstance(node.left, Literal):
                        if isinstance(node.right, Literal):
                            return Literal(node.left.value + node.right.value)
                        return binop('+', node.right, node.left)
                    # reduces single variables
                    if isinstance(node.left, Variable) and isinstance(node.right, Variable) and node.left.name == node.right.name:
                        return BinaryOp('*', Literal(2), node.left)
                    # move literals right
                    if self._almost_literal(node.left) and not self._almost_literal(node.right):
                        return binop('+', node.right, node.left)
                    # reduces fractions
                    if self._is_binop(node.left, '/'):
                        return binop('/', binop('+', node.left.left, binop('*', node.left.right, node.right)), node.left.right)
                    # reduces stacks of "+" ; combines literals in "+" trees ; reorder variables
                    if self._is_binop(node.left, '+'):
                        if self._almost_literal(node.left.right):
                            if self._almost_literal(node.right):
                                return binop('+', node.left.left, binop('+', node.left.right, node.right))
                            return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if isinstance(node.left.right, Variable) and isinstance(node.right, Variable):
                            if node.left.right.name == node.right.name:
                                return binop('+', node.left.left, BinaryOp('*', Literal(2), node.right))
                            if self._is_unsorted(node.left.right.name, node.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if self._is_binop(node.left.right, '*') and isinstance(node.left.right.right, Variable) and isinstance(node.right, Variable):
                            if node.left.right.right.name == node.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.left.right.left, Literal(1)), node.right))
                            if self._is_unsorted(node.left.right.right.name, node.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if isinstance(node.left.right, Variable) and self._is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                            if node.left.right.name == node.right.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.right.left, Literal(1)), node.left.right))
                            if self._is_unsorted(node.left.right.name, node.right.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if self._is_binop(node.left.right, '*') and isinstance(node.left.right.right, Variable) and self._is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                            if node.left.right.right.name == node.right.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.right.left, Literal(1)), node.right.right))
                            if self._is_unsorted(node.left.right.right.name, node.right.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                    # reduces and reorder variables
                    if isinstance(node.left, Variable) and self._is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                        if node.right.right.name == node.left.name:
                            return binop('*', binop('+', node.right.left, Literal(1)), node.left)
                        if self._is_unsorted(node.left.name, node.right.right.name):
                            return binop('+', node.right, node.left)
                    if isinstance(node.right, Variable) and self._is_binop(node.left, '*') and isinstance(node.left.right, Variable):
                        if node.left.right.name == node.right.name:
                            return binop('*', binop('+', node.left.left, Literal(1)), node.right)
                        if self._is_unsorted(node.left.right.name, node.right.name):
                            return binop('+', node.right, node.left)
                    if self._is_binop(node.left, '*') and isinstance(node.left.right, Variable) and self._is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                        if node.left.right.name == node.right.right.name:
                            return binop('*', binop('+', node.left.left, node.right.left), node.right.right)
                        if self._is_unsorted(node.left.right.name, node.right.right.name):
                            return binop('+', node.right, node.left)
                # rewrite xor
                if node.op == 'xor':
                    return binop('and', binop('or', node.left, node.right), unaop('not', binop('and', node.left, node.right)))
                # rewrite if
                if node.op == 'if':
                    return binop('or', node.left, unaop('not', node.right))
                # rewrite iif
                if node.op == 'iif':
                    return binop('and', binop('if', node.left, node.right), binop('if', node.right, node.left))
                # simplify and
                if node.op == 'and':
                    if str(node.left) == str(node.right):
                        return node.left
                    if str(node.left) == 'True' or str(node.right) == 'False':
                        return node.right
                    if str(node.left) == 'False' or str(node.right) == 'True':
                        return node.left
                    if self._almost_variable(node.left) and self._almost_variable(node.right):
                        if str(node.left) == str(unaop('not', node.right)):
                            return Literal(False)
                    # rebalance left
                    if self._is_binop(node.right, 'and'):
                        return binop('and', binop('and', node.left, node.right.left), node.right.right)
                    # sort and variables
                    if self._is_binop(node.left, 'and'):
                        tmp_l = node.left.right
                        tmp_r = node.right
                        if self._is_unaop(tmp_l, 'not'):
                            tmp_l = tmp_l.right
                        if self._is_unaop(tmp_r, 'not'):
                            tmp_r = tmp_r.right
                        if isinstance(tmp_l, Variable) and isinstance(tmp_r, Variable) and self._is_unsorted(tmp_l.name, tmp_r.name):
                            return binop('and', binop('and', node.left.left, node.right), node.left.right)
                # simplify or
                if node.op == 'or':
                    if str(node.left) == str(node.right):
                        return node.left
                    if str(node.left) == 'True' or str(node.right) == 'False':
                        return node.left
                    if str(node.left) == 'False' or str(node.right) == 'True':
                        return node.right
                    if self._almost_variable(node.left) and self._almost_variable(node.right):
                        if str(node.left) == str(unaop('not', node.right)):
                            return Literal(True)
                    # rebalance left
                    if self._is_binop(node.right, 'or'):
                        return binop('or', binop('or', node.left, node.right.left), node.right.right)
                    # distribute or
                    if self._is_binop(node.right, 'and'):
                        return binop('and', binop('or', node.left, node.right.left), binop('or', node.left, node.right.right))
                    if self._is_binop(node.left, 'and'):
                        return binop('and', binop('or', node.left.left, node.right), binop('or', node.left.right, node.right))
                    # sort or variables
                    if self._is_binop(node.left, 'or'):
                        tmp_l = node.left.right
                        tmp_r = node.right
                        if self._is_unaop(tmp_l, 'not'):
                            tmp_l = tmp_l.right
                        if self._is_unaop(tmp_r, 'not'):
                            tmp_r = tmp_r.right
                        if isinstance(tmp_l, Variable) and isinstance(tmp_r, Variable) and self._is_unsorted(tmp_l.name, tmp_r.name):
                            return binop('or', binop('or', node.left.left, node.right), node.left.right)
                if node.op in {'<', '>', '<=', '>=', '==', '!='}:
                    if self._almost_literal(node.left):
                        if self._almost_literal(node.right):
                            return Literal(node.evaluate({}))
                        return binop(node.op, unaop('-', node.right), unaop('-', node.left))
                    if not self._almost_literal(node.right):
                        return binop(node.op, binop('-', node.left, node.right), Literal(0))
                    if self._is_binop(node.left, '+'):
                        if self._almost_literal(node.left.right):
                            return binop(node.op, node.left.left, binop('-', node.right, node.left.right))
                    if self._is_binop(node.right, '/'):
                        return binop(node.op, binop('*', node.right.right, node.left), node.right.left)
                    if coefs := list(self._denominators(node.left, set())):
                        return binop(node.op, binop('*', Literal(max(coefs)), node.left), binop('*', Literal(max(coefs)), node.right))
                    coefs = list(self._nominators(node.left, set()))
                    tmp = list(self._nominators(node.right, set()))
                    if 1 not in coefs:
                        if tmp != [0]:
                            coefs.append(tmp[0])
                        g = math.gcd(*[abs(x) for x in coefs])
                        if g > 1:
                            return binop(node.op, binop('/', node.left, Literal(g)), binop('/', node.right, Literal(g)))
                if node.op == '<':
                    return binop('<=', node.left, node.right)
                if node.op == '>':
                    return binop('>=', node.left, node.right)
                if node.op == '>=':
                    if isinstance(node.right, Literal) and node.right.value == 0 and self._is_binop(node.left, '*'):
                        if node.left.left.value > 0:
                            return binop('>=', node.left.right, node.right)
                        return binop('<=', node.left.right, node.right)
                if node.op == '<=':
                    if isinstance(node.right, Literal) and node.right.value == 0 and self._is_binop(node.left, '*'):
                        if node.left.left.value > 0:
                            return binop('<=', node.left.right, node.right)
                        return binop('>=', node.left.right, node.right)
        return node

    def _canonical_visitor(self, node):
        def unaop(op, right):
            return self._normalize_visitor(UnaryOp(op, right))
        def binop(op, left, right):
            return self._normalize_visitor(BinaryOp(op, left, right))

        match node:
            case Objective():
                if node.mode == 'min':
                    return Objective('max', unaop('-', node.var), unaop('-', node.right))
            case BinaryOp():
                if node.op == '==':
                    return binop('and', binop('<=', node.left, node.right), binop('>=', node.left, node.right))
                if node.op == '!=':
                    return binop('or', binop('<', node.left, node.right), binop('>', node.left, node.right))
                if node.op == '>=':
                    return binop('<=', unaop('-', node.left), unaop('-', node.right))
        return node

    def normalize(self, program):
        self.variables = program.variables[:]
        program.root = program.root.rewrite(self._normalize_visitor)

    def do_canonical(self, program):
        self.normalize(program)
        program.root = program.root.rewrite(self._canonical_visitor)

