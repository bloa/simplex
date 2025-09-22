import abc


class AbstractSolver:
    def __init__(self):
        pass

    @abc.abstractmethod
    def solve(self, model):
        pass
