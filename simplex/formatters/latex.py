import re

from simplex.core import AbstractFormatter, Rewriter
from simplex.parsing import BinaryOp, ExprTree, Literal, UnaryOp, Variable
from simplex.utils import prefix_sort


class AbstractLatexFormatter(AbstractFormatter):
    @staticmethod
    def text_to_latex(e):
        s = str(e)
        s = re.sub(r'_', r'\\_', s)
        s = re.sub(r'<=', r'$\\leq$', s)
        s = re.sub(r'>=', r'$\\geq$', s)
        s = re.sub(r'(-|\+|=)', r'$\1$', s)
        s = re.sub(r'(?<!_)([a-z]+)(\d+)', r'$\1_\2$', s)
        s = re.sub(r'(-?\d+)/(\d+)', r'$(\\nicefrac{\1}{\2})$', s)
        s = re.sub(r'\$(\s*\d+\.?\d*)', r'\1$', s)
        s = re.sub(r'\$(\s*)\$', r'\1', s)
        return s

    @staticmethod
    def math_to_latex(e):
        s = str(e)
        s = re.sub(r'<=', r'\\leq', s)
        s = re.sub(r'>=', r'\\geq', s)
        s = re.sub(r'(\w+)(\d+)', r'\1_\2', s)
        s = re.sub(r'(-?\d+)/(\d+)', r'(\\nicefrac{\1}{\2})', s)
        return s

    def format_section(self, title):
        out = []
        out.append(fr'\subsection*{{{self.text_to_latex(title)}}}')
        return '\n'.join(out)

    def format_step(self, title):
        out = []
        out.append(fr'\subsubsection*{{{self.text_to_latex(title)}}}')
        return '\n'.join(out)

    def format_action(self, text):
        return fr'{self.text_to_latex(text)}\\'

    def format_info(self, text):
        return fr'\-\quad {self.text_to_latex(text)}\\'

    def format_decision(self, text):
        return fr'\-\quad → {self.text_to_latex(text)}\\'

    def format_raw_model(self, raw):
        return ''

    @classmethod
    def _aux(cls, tree, variables):
        def pseudo_visitor(node, acc):
            match node:
                case BinaryOp(op='+'):
                    pseudo_visitor(node.left, acc)
                    pseudo_visitor(node.right, acc)
                case BinaryOp(op='*'):
                    acc[node.right.name] = cls.math_to_latex(str(node.left))
                case UnaryOp(op='-'):
                    pseudo_visitor(node.right, acc)
                    acc[node.right.name] = '-' + acc[node.right.name]
                case Variable():
                    acc[node.name] = ''
                case BinaryOp(op='<=') | BinaryOp(op='>=') | BinaryOp(op='==') | BinaryOp(op='='):
                    acc['op'] = cls.math_to_latex(node.op)
                    pseudo_visitor(node.left, acc)
                    pseudo_visitor(node.right, acc)
                case Literal():
                    acc['rhs'] = cls.math_to_latex(node.value)
                case _:
                    raise NotImplementedError
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
                out.append(tmp[v] + cls.math_to_latex(v))
            else:
                out.append('')
                out.append('')
        if tmp['op']:
            out.append(tmp['op'])
            out.append(tmp['rhs'])
        return out[1:]

    def format_objective(self, model):
        variables = model.variables[:]
        variables.remove(model.objective.root.var().name)
        out = []
        out.append(r'\begin{equation*}')
        out.append(r'  \arraycolsep=0.3em')
        out.append(r'  \begin{array}{rr' + 'cr'*len(variables) + '}')
        tmp = self._aux(model.objective.root.right, variables)
        out.append(r'    \text{' + model.objective.root.mode + 'imise' + '} & ' + self.math_to_latex(str(model.objective.root.var)) + ' = ' + ' & '.join(tmp) + r'\\')
        out.append(r'  \end{array}')
        out.append(r'\end{equation*}')
        return '\n'.join(out)

    def format_model(self, model):
        variables = model.variables[:]
        variables.remove(model.objective.root.var().name)
        out = []
        out.append(r'\begin{equation*}')
        out.append(r'  \arraycolsep=0.3em')
        out.append(r'  \begin{array}{rr' + 'cr'*len(variables) + '}')
        tmp = self._aux(model.objective.root.right, variables)
        out.append(r'    \text{' + model.objective.root.mode + 'imise' + '} & ' + self.math_to_latex(str(model.objective.root.left)) + ' = ' + ' & '.join(tmp) + r'\\')
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
                tmp = self._aux(e, variables)
                if k == 0:
                    out.append(r'    \text{subject to} & ' + ' & '.join(tmp) + r'\\')
                else:
                    out.append(r'    & ' + ' & '.join(tmp) + r'\\')
        if neg_var:
            tmp = ', '.join(prefix_sort(neg_var))
            out.append(r'    & \multicolumn{' + str(2*len(variables)-1) + '}{r}{' + self.math_to_latex(tmp) + r'} & \leq & 0\\')
        if pos_var:
            tmp = ', '.join(prefix_sort(pos_var))
            out.append(r'    & \multicolumn{' + str(2*len(variables)-1) + '}{r}{' + self.math_to_latex(tmp) + r'} & \geq & 0\\')
        out.append(r'  \end{array}')
        out.append(r'\end{equation*}')
        return '\n'.join(out)

    def format_summary(self, summary, renames):
        out = []
        status = summary['status']
        out.append(fr'\textbf{{{status}}}')
        if summary['values']:
            out.append(r'\begin{align*}')
            for k, v in summary['values'].items():
                tmp = f'    {self.math_to_latex(k)} & '
                if k in renames:
                    tmp += f' = {self.math_to_latex(renames[k])}'
                tmp += f' = {self.math_to_latex(v)}'
                e = ExprTree.from_string(str(v))
                Rewriter().normalize(e)
                v2 = e.evaluate({})
                if str(e) != str(v2):
                    tmp += f' = {round(v2, 8)}'
                tmp += r'\\'
                out.append(tmp)
            out.append(r'\end{align*}')
        return '\n'.join(out)
