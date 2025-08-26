import math

from .expr_nodes import (
    BinaryOp,
    ExprList,
    Literal,
    Objective,
    UnaryOp,
    Variable,
)
from .expr_tokenizer import tokenize
from .parser import Parser


class ExprTree:
    @classmethod
    def from_string(cls, s):
        tokens = tokenize(s)
        return cls(Parser(tokens).parse())

    def __init__(self, root):
        self.root = root
        self.variables = self._find_variables(self.root)
        self._check_for_obvious_typing_errors(self.root)

    def __str__(self):
        return str(self.root)

    def evaluate(self, context):
        return self.root.evaluate(context)

    def normalize(self):
        def almost_literal(node):
            if isinstance(node, Literal):
                return True
            if isinstance(node, UnaryOp):
                return almost_literal(node.right)
            if isinstance(node, BinaryOp):
                return almost_literal(node.left) and almost_literal(node.right)
            return False
        def almost_variable(node, single=False):
            if isinstance(node, ExprList):
                return all(almost_variable(e) for e in node.exprlist)
            if isinstance(node, Variable):
                return True
            if isinstance(node, UnaryOp):
                return almost_variable(node.right)
            if isinstance(node, BinaryOp) and (single or node.op == '*'):
                return almost_literal(node.left) and almost_variable(node.right)
            return False
        def is_unaop(expr, op):
            return isinstance(expr, UnaryOp) and expr.op == op
        def is_binop(expr, op):
            return isinstance(expr, BinaryOp) and expr.op == op
        def nominators(node, acc):
            if isinstance(node, Literal):
                return acc | {node.value}
            if isinstance(node, Variable):
                return acc | {1}
            if isinstance(node, ExprList):
                return acc | {1}
            if isinstance(node, BinaryOp) and node.op in {'+', '-'}:
                return nominators(node.right, nominators(node.left, acc))
            if isinstance(node, BinaryOp) and node.op == '*':
                return nominators(node.left, acc)
            return acc
        def denominators(node, acc):
            if is_binop(node, '/'):
                return acc | nominators(node.right, set())
            if isinstance(node, UnaryOp):
                return denominators(node.right, acc)
            if isinstance(node, BinaryOp) and node.op in {'+', '-', '*'}:
                return denominators(node.right, denominators(node.left, acc))
            return acc
        def unaop(op, right):
            return visitor(UnaryOp(op, right))
        def binop(op, left, right):
            return visitor(BinaryOp(op, left, right))
        def is_unsorted(variables, left, right):
            return variables.index(left) > variables.index(right)
        def visitor(node):
            if isinstance(node, Literal):
                if '.' in str(node.value):
                    i = int(node.value)
                    f = node.value - i
                    n = len(str(f)) - 2
                    if f == 0:
                        return Literal(i)
                    return binop('/', Literal(int(10**n*node.value)), Literal(10**n))
            if isinstance(node, Objective):
                if node.mode == 'min':
                    return Objective('max', unaop('-', node.var), unaop('-', node.right))
                if isinstance(node.var, BinaryOp):
                    if isinstance(node.var.left, Literal):
                        if node.var.left.value > 0:
                            return Objective(node.mode, node.var.right, binop('/', node.right, node.var.left))
                        if node.var.left.value != -1:
                            return Objective(node.mode, unaop('-', node.var.right), binop('/', node.right, node.var.left))
                    elif is_binop(node.var.left, '/'):
                        if node.var.left.left.value > 0:
                            return Objective(node.mode, node.var.right, binop('*', binop('/', node.var.left.right, node.var.left.left), node.right))
                        if node.var.left.left.value != -1:
                            return Objective(node.mode, unaop('-', node.var.right), binop('*', binop('/', node.var.left.right, node.var.left.left), node.right))
            if isinstance(node, UnaryOp):
                # simplify repeated unary ops
                if isinstance(node.right, UnaryOp) and node.op == node.right.op:
                    return node.right.right
                # rewrite unary "-"
                if node.op == '-':
                    if isinstance(node.right, Literal):
                        return Literal(-node.right.value)
                    if isinstance(node.right, Variable):
                        return binop('*', Literal(-1), node.right)
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
                    if isinstance(node.right, BinaryOp):
                        if node.right.op == 'or':
                            return binop('and', unaop('not', node.right.left), unaop('not', node.right.right))
                        if node.right.op == 'and':
                            return binop('or', unaop('not', node.right.left), unaop('not', node.right.right))
                        h = {'>': '<=', '<': '>=', '>=': '<', '<=': '>', '==': '!=', '!=': '=='}
                        return binop(h[node.right.op], node.right.left, node.right.right)
            if isinstance(node, BinaryOp):
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
                        if is_binop(node.right, '+'):
                            return binop('+', binop('*', node.left, node.right.left), binop('*', node.left, node.right.right))
                        if is_binop(node.right, '*'):
                            return binop('*', binop('*', node.left, node.right.left), node.right.right)
                    # distribute "*" inside "/"
                    if isinstance(node.right, BinaryOp) and node.right.op == '/':
                            return binop('/', binop('*', node.left, node.right.left), node.right.right)
                if node.op == '/':
                    # move variables outside divisions
                    if isinstance(node.left, Variable):
                        return binop('*', binop('/', Literal(1), node.right), node.left)
                    if is_binop(node.left, '*'):
                        return binop('*', binop('/', node.left.left, node.right), node.left.right)
                    if is_binop(node.left, '+'):
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
                    if is_binop(node.left, '/'):
                        return binop('/', node.left.left, binop('*', node.left.right, node.right))
                    if is_binop(node.right, '/'):
                        return binop('/', binop('*', node.left, node.right.right), node.right.left)
                if node.op == '+':
                    # reduce literals
                    if isinstance(node.left, Literal):
                        if isinstance(node.right, Literal):
                            return Literal(node.left.value + node.right.value)
                        return binop('+', node.right, node.left)
                    # reduces single variables
                    if isinstance(node.left, Variable) and isinstance(node.right, Variable) and node.left.name == node.right.name:
                        return BinaryOp('*', Literal(2), node.left)
                    # move literals right
                    if almost_literal(node.left) and not almost_literal(node.right):
                        return binop('+', node.right, node.left)
                    # reduces fractions
                    if is_binop(node.left, '/'):
                        return binop('/', binop('+', node.left.left, binop('*', node.left.right, node.right)), node.left.right)
                    # reduces stacks of "+" ; combines literals in "+" trees ; reorder variables
                    if is_binop(node.left, '+'):
                        if almost_literal(node.left.right):
                            if almost_literal(node.right):
                                return binop('+', node.left.left, binop('+', node.left.right, node.right))
                            return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if is_binop(node.right, '+') and almost_literal(node.right.right):
                            return binop('+', binop('+', node.left.left, node.right.left), binop('+', node.left.right, node.right.right))
                        if isinstance(node.left.right, Variable) and isinstance(node.right, Variable):
                            if node.left.right.name == node.right.name:
                                return binop('+', node.left.left, BinaryOp('*', Literal(2), node.right))
                            if self.variables.index(node.right.name) < self.variables.index(node.left.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if is_binop(node.left.right, '*') and isinstance(node.left.right.right, Variable) and isinstance(node.right, Variable):
                            if node.left.right.right.name == node.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.left.right.left, Literal(1)), node.right))
                            if self.variables.index(node.right.name) < self.variables.index(node.left.right.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if isinstance(node.left.right, Variable) and is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                            if node.left.right.name == node.right.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.right.left, Literal(1)), node.left.right))
                            if is_unsorted(self.variables, node.left.right.name, node.right.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                        if is_binop(node.left.right, '*') and isinstance(node.left.right.right, Variable) and is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                            if node.left.right.right.name == node.right.right.name:
                                return binop('+', node.left.left, binop('*', binop('+', node.right.left, Literal(1)), node.right.right))
                            if self.variables.index(node.right.right.name) < self.variables.index(node.left.right.right.name):
                                return binop('+', binop('+', node.left.left, node.right), node.left.right)
                    # linearize "+" trees
                    if is_binop(node.right, '+'):
                        return binop('+', binop('+', node.left, node.right.left), node.right.right)
                    # reduces and reorder variables
                    if isinstance(node.left, Variable) and is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                        if node.right.right.name == node.left.name:
                            return binop('*', binop('+', node.right.left, Literal(1)), node.left)
                        if self.variables.index(node.right.right.name) < self.variables.index(node.left.name):
                            return binop('+', node.right, node.left)
                    if isinstance(node.right, Variable) and is_binop(node.left, '*') and isinstance(node.left.right, Variable):
                        if node.left.right.name == node.right.name:
                            return binop('*', binop('+', node.left.left, Literal(1)), node.right)
                        if is_unsorted(self.variables, node.left.right.name, node.right.name):
                            return binop('+', node.right, node.left)
                    if is_binop(node.left, '*') and isinstance(node.left.right, Variable) and is_binop(node.right, '*') and isinstance(node.right.right, Variable):
                        if node.left.right.name == node.right.right.name:
                            return binop('*', binop('+', node.left.left, node.right.left), node.right.right)
                        if is_unsorted(self.variables, node.left.right.name, node.right.right.name):
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
                    if almost_variable(node.left) and almost_variable(node.right):
                        if str(node.left) == str(unaop('not', node.right)):
                            return Literal(False)
                    # rebalance left
                    if is_binop(node.right, 'and'):
                        return binop('and', binop('and', node.left, node.right.left), node.right.right)
                    # sort and variables
                    if is_binop(node.left, 'and'):
                        tmp_l = node.left.right
                        tmp_r = node.right
                        if is_unaop(tmp_l, 'not'):
                            tmp_l = tmp_l.right
                        if is_unaop(tmp_r, 'not'):
                            tmp_r = tmp_r.right
                        if isinstance(tmp_l, Variable) and isinstance(tmp_r, Variable) and is_unsorted(self.variables, tmp_l.name, tmp_r.name):
                            return binop('and', binop('and', node.left.left, node.right), node.left.right)
                # simplify or
                if node.op == 'or':
                    if str(node.left) == str(node.right):
                        return node.left
                    if str(node.left) == 'True' or str(node.right) == 'False':
                        return node.left
                    if str(node.left) == 'False' or str(node.right) == 'True':
                        return node.right
                    if almost_variable(node.left) and almost_variable(node.right):
                        if str(node.left) == str(unaop('not', node.right)):
                            return Literal(True)
                    # rebalance left
                    if is_binop(node.right, 'or'):
                        return binop('or', binop('or', node.left, node.right.left), node.right.right)
                    # distribute or
                    if is_binop(node.right, 'and'):
                        return binop('and', binop('or', node.left, node.right.left), binop('or', node.left, node.right.right))
                    if is_binop(node.left, 'and'):
                        return binop('and', binop('or', node.left.left, node.right), binop('or', node.left.right, node.right))
                    # sort or variables
                    if is_binop(node.left, 'or'):
                        tmp_l = node.left.right
                        tmp_r = node.right
                        if is_unaop(tmp_l, 'not'):
                            tmp_l = tmp_l.right
                        if is_unaop(tmp_r, 'not'):
                            tmp_r = tmp_r.right
                        if isinstance(tmp_l, Variable) and isinstance(tmp_r, Variable) and is_unsorted(self.variables, tmp_l.name, tmp_r.name):
                            return binop('or', binop('or', node.left.left, node.right), node.left.right)
                if node.op == '==':
                    return binop('and', binop('<=', node.left, node.right), binop('>=', node.left, node.right))
                if node.op == '!=':
                    return binop('or', binop('<', node.left, node.right), binop('>', node.left, node.right))
                if node.op == '<':
                    return binop('<=', node.left, node.right)
                if node.op == '>':
                    return binop('>=', node.left, node.right)
                if node.op == '>=':
                    if not (almost_variable(node.left, single=True) and isinstance(node.right, Literal) and node.right.value == 0):
                        return binop('<=', node.right, node.left)
                if node.op == '<=':
                    if isinstance(node.right, Literal) and node.right.value == 0 and is_binop(node.left, '*'):
                        if node.left.left.value > 0:
                            return binop('<=', node.left.right, node.right)
                        return binop('>=', node.left.right, node.right)
                if node.op in {'<', '>', '<=', '>=', '==', '!='}:
                    if not almost_literal(node.right):
                        return binop(node.op, binop('-', node.left, node.right), Literal(0))
                    if is_binop(node.left, '+'):
                        if almost_literal(node.left.right):
                            return binop(node.op, node.left.left, binop('-', node.right, node.left.right))
                    if is_binop(node.right, '/'):
                        return binop(node.op, binop('*', node.right.right, node.left), node.right.left)
                    if coefs := list(denominators(node.left, set())):
                        return binop(node.op, binop('*', Literal(max(coefs)), node.left), binop('*', Literal(max(coefs)), node.right))
                    coefs = list(nominators(node.left, set()))
                    tmp = list(nominators(node.right, set()))
                    if 1 not in coefs:
                        if tmp != [0]:
                            coefs.append(tmp[0])
                        g = math.gcd(*[abs(x) for x in coefs])
                        if g > 1:
                            return binop(node.op, binop('/', node.left, Literal(g)), binop('/', node.right, Literal(g)))
            return node
        self.root = self.root.rewrite(visitor)

    def rename(self, old, new):
        if old not in self.variables:
            return
        def visitor(node):
            if isinstance(node, Variable) and node.name == old:
                node.name = new
        self.root.visit(visitor)
        self.variables = {new if var == old else var for var in self.variables}

    def replace(self, old, new):
        def visitor(node):
            if str(node) == str(old):
                return new
            return node
        self.root = self.root.rewrite(visitor)
        self.variables = self._find_variables(self.root)

    def _find_variables(self, root):
        variables = []
        def visitor(node):
            nonlocal variables
            if isinstance(node, Variable) and node.name not in variables:
                variables.append(node.name)
        root.visit(visitor)
        return variables

    def _is_obvious_math(self, node):
        if isinstance(node, Literal):
            return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
        if isinstance(node, BinaryOp):
            return node.op in {'+', '-', '*', '/'}
        if isinstance(node, UnaryOp):
            return node.op == '-'
        return False

    def _is_obvious_bool(self, node):
        if isinstance(node, Literal):
            return isinstance(node.value, bool)
        if isinstance(node, BinaryOp):
            return node.op in {'==', '!=', '<=', '>=', '<', '>', 'and', 'or', 'xor'}
        if isinstance(node, UnaryOp):
            return node.op == 'not'
        return False

    BOOL_FOUND_BUT_NUM_EXPECTED = 'Expression appears to be Boolean, but a numeric expression was expected'
    NUM_FOUND_BUT_BOOL_EXPECTED = 'Expression appears to be numeric, but a Boolean expression was expected'

    def _check_for_obvious_typing_errors(self, node):
        def visitor(node):
            if isinstance(node, BinaryOp):
                math_left = self._is_obvious_math(node.left)
                math_right = self._is_obvious_math(node.right)
                bool_left = self._is_obvious_bool(node.left)
                bool_right = self._is_obvious_bool(node.right)
                if node.op in {'+', '-', '*', '/', '<=', '>=', '<', '>'} and (bool_left or bool_right):
                    raise TypeError(self.BOOL_FOUND_BUT_NUM_EXPECTED)
                if node.op in {'and', 'or'} and (math_left or math_right):
                    raise TypeError(self.NUM_FOUND_BUT_BOOL_EXPECTED)
            elif isinstance(node, UnaryOp):
                math_right = self._is_obvious_math(node.right)
                bool_right = self._is_obvious_bool(node.right)
                if node.op == '-' and bool_right:
                    raise TypeError(self.BOOL_FOUND_BUT_NUM_EXPECTED)
                if node.op == 'not' and math_right:
                    raise TypeError(self.NUM_FOUND_BUT_BOOL_EXPECTED)
        node.visit(visitor)

class LinExprTree(ExprTree):
    def __init__(self, s):
        super().__init__(s)
        def visitor(node):
            if (isinstance(node, BinaryOp) and
                ((node.op == '*' and self._check_if_variable(node.left) and self._check_if_variable(node.right)) or
                 (node.op == '/' and self._check_if_variable(node.right)))):
                msg = 'Invalid non-linear expression'
                raise TypeError(msg)
        self.root.visit(visitor)

    def _check_if_variable(self, node):
        b = False
        def visitor(node):
            nonlocal b
            if isinstance(node, Variable):
                b = True
        node.visit(visitor)
        return b

class MathTree(LinExprTree):
    def __init__(self, s):
        super().__init__(s)
        def visitor(node):
            if self._is_obvious_bool(node):
                msg = 'Invalid Boolean operator in numerical expression'
                raise TypeError(msg)
        self.root.visit(visitor)

    def evaluate(self, context):
        result = super().evaluate(context)
        if not isinstance(result, (int, float)):
            msg = f'Expression evaluated to "{result}", but a numeric value was expected'
            raise TypeError(msg)
        return result

class BoolTree(LinExprTree):
    def __init__(self, s):
        super().__init__(s)
        if self._is_obvious_math(self.root):
            raise TypeError(self.NUM_FOUND_BUT_BOOL_EXPECTED)

    def evaluate(self, context):
        result = super().evaluate(context)
        if not isinstance(result, bool):
            msg = 'Expression evaluated to a numeric value, but a Boolean value was expected'
            raise TypeError(msg)
        return result

class ObjectiveTree(LinExprTree):
    def __init__(self, s):
        super().__init__(s)
        if not isinstance(self.root, Objective):
            msg = 'Invalid expression in objective function'
            raise TypeError(msg)
        if not isinstance(self.root.var, Variable) or (isinstance(self.root.var, UnaryOp) and self.root.var.op == '-' and isinstance(self.root.var.right, Variable)):
            msg = 'Invalid expression in objective function variable'
            raise SyntaxError(msg)
        def visitor(node):
            if self._is_obvious_bool(node):
                msg = 'Invalid Boolean operator in numerical expression'
                raise TypeError(msg)
        self.root.right.visit(visitor)
        var = self.root.var
        def visitor(node):
            nonlocal var
            if isinstance(node, Variable) and node.name == var.name:
                msg = 'Invalid variable in objective expression'
                raise SyntaxError(msg)
        self.root.right.visit(visitor)
