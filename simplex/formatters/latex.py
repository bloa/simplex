import re

from simplex.core import AbstractFormatter
from simplex.parsing import BinaryOp, Literal, UnaryOp, Variable
from simplex.utils import prefix_sort


class AbstractLatexFormatter(AbstractFormatter):
    @staticmethod
    def var_to_latex(var):
        if m := re.match(r'(\w+)(\d+)', var):
            return f'{m.group(1)}_{m.group(2)}'
        return var

    @staticmethod
    def math_to_latex(e):
        s = str(e)
        if m := re.match(r'(.*)/(.*)', s):
            return rf'(\nicefrac{{{m.group(1)}}}{{{m.group(2)}}})'
        return s

    @staticmethod
    def op_to_latex(op):
        match op:
            case '<=':
                return r'\leq'
            case '>=':
                return r'\geq'
        return op

    def format_model(self, model):
        def pseudo_visitor(node, acc):
            match node:
                case BinaryOp(op='+'):
                    pseudo_visitor(node.left, acc)
                    pseudo_visitor(node.right, acc)
                case BinaryOp(op='*'):
                    acc[node.right.name] = self.math_to_latex(node.left.value)
                case UnaryOp(op='-'):
                    pseudo_visitor(node.right, acc)
                    acc[node.right.name] = '-' + acc[node.right.name]
                case Variable():
                    acc[node.name] = ''
                case BinaryOp(op='<=') | BinaryOp(op='>=') | BinaryOp(op='==') | BinaryOp(op='='):
                    acc['op'] = self.op_to_latex(node.op)
                    pseudo_visitor(node.left, acc)
                    pseudo_visitor(node.right, acc)
                case Literal():
                    acc['rhs'] = self.math_to_latex(node.value)
                case _:
                    print(node)
                    raise NotImplementedError
        def aux(tree, variables):
            # compute each coefficient
            tmp = {k: None for k in variables}
            tmp['op'] = None
            tmp['rhs'] = None
            pseudo_visitor(tree, tmp)
            # translate into latex
            out = []
            first = True
            for v in variables:
                if tmp[v] is not None:
                    if first:
                        first = False
                        out.append('')
                    else:
                        out.append('+')
                    out.append(tmp[v] + self.var_to_latex(v))
                else:
                    out.append('')
                    out.append('')
            if tmp['op']:
                out.append(tmp['op'])
                out.append(tmp['rhs'])
            return out[1:]
        variables = model.variables[:]
        obj_var = model.objective.root.var
        while not isinstance(obj_var, Variable):
            obj_var = obj_var.right
        variables.remove(obj_var.name)
        out = []
        out.append(r'\begin{equation*}')
        out.append(r'  \arraycolsep=0.3em')
        out.append(r'  \begin{array}{rr' + 'cr'*len(variables) + '}')
        tmp = aux(model.objective.root.right, variables)
        out.append(r'    \text{' + model.objective.root.mode + 'imise' + '} & ' + self.var_to_latex(str(model.objective.root.var)) + ' = ' + ' & '.join(tmp) + r'\\')
        neg_var = []
        pos_var = []
        for k, c in enumerate(model.constraints):
            e = c.root
            if isinstance(e, BinaryOp) and isinstance(e.left, Variable) and isinstance(e.right, Literal) and e.right.value == 0:
                if e.op == '<=':
                    neg_var.append(e.left.name)
                elif e.op == '>=':
                    pos_var.append(e.left.name)
            else:
                tmp = aux(e, variables)
                if k == 0:
                    out.append(r'    \text{subject to} & ' + ' & '.join(tmp) + r'\\')
                else:
                    out.append(r'    & ' + ' & '.join(tmp) + r'\\')
        if neg_var:
            tmp = ', '.join(prefix_sort([self.var_to_latex(v) for v in neg_var]))
            out.append(r'    & \multicolumn{' + str(2*len(variables)-1) + '}{r}{' + tmp + r'} & \leq & 0\\')
        if pos_var:
            tmp = ', '.join(prefix_sort([self.var_to_latex(v) for v in pos_var]))
            out.append(r'    & \multicolumn{' + str(2*len(variables)-1) + '}{r}{' + tmp + r'} & \geq & 0\\')
        out.append(r'  \end{array}')
        out.append(r'\end{equation*}')
        return '\n'.join(out)
