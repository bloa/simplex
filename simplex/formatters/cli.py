from simplex.core import AbstractFormatter
from simplex.parsing import BinaryOp, ExprList, Literal, Variable
from simplex.utils import prefix_sort


class AbstractCliFormatter(AbstractFormatter):
    @staticmethod
    def format_model(model):
        tmp = [str(model.objective)]
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
                tmp.append(str(e))
        if neg_var:
            tmp.append(str(BinaryOp('<=', ExprList(prefix_sort(neg_var)), Literal(0))))
        if pos_var:
            tmp.append(str(BinaryOp('>=', ExprList(prefix_sort(pos_var)), Literal(0))))
        return '\n'.join(tmp)
