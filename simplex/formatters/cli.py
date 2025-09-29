from simplex.core import AbstractFormatter, Rewriter
from simplex.parsing import BinaryOp, ExprList, ExprTree, Literal, Variable
from simplex.utils import prefix_sort


class AbstractCliFormatter(AbstractFormatter):
    @staticmethod
    def bold(text):
        return f'\033[1m{text}\033[0m'

    @staticmethod
    def indent(lines):
        out = [f'    {line}' for line in lines]
        return '\n'.join(out)

    def format_section(self, title):
        out = []
        out.append(self.bold(f'# {title}'))
        out.append(self.bold('-----------------------------------'))
        return '\n'.join(out)

    def format_step(self, title):
        return self.bold(f'* {title}')

    def format_action(self, text):
        return text

    def format_info(self, text):
        return f'  ... {text}'

    def format_decision(self, text):
        return f'  -> {text}'

    def format_raw_model(self, raw):
        out = [line for line in raw.split('\n') if line.strip()]
        return self.indent(out)

    def format_objective(self, model):
        return self.indent([str(model.objective)])

    def format_model(self, model):
        out = [str(model.objective)]
        neg_var = []
        pos_var = []
        for c in model.constraints:
            e = c.root
            if isinstance(e, BinaryOp) and isinstance(e.left, Variable) and isinstance(e.right, Literal) and e.right.value == 0:
                if e.op == '<=':
                    neg_var.append(e.left.name)
                elif e.op == '>=':
                    pos_var.append(e.left.name)
            else:
                out.append(str(e))
        if neg_var:
            out.append(str(BinaryOp('<=', ExprList(prefix_sort(neg_var)), Literal(0))))
        if pos_var:
            out.append(str(BinaryOp('>=', ExprList(prefix_sort(pos_var)), Literal(0))))
        return self.indent(out)

    def format_summary(self, summary, renames):
        out = []
        status = summary['status']
        out.append(f'Status: {self.bold(status)}')
        if summary['values']:
            out.append('Final values:')
            for k, v in summary['values'].items():
                tmp = f'    {k}'
                if k in renames:
                    tmp += f' = {renames[k]}'
                tmp += f' = {v}'
                e = ExprTree.from_string(str(v))
                Rewriter().normalize(e)
                v2 = e.evaluate({})
                if str(e) != str(v2):
                    tmp += f' = {round(v2, 8)}'
                out.append(tmp)
        return '\n'.join(out)
