import abc


class AbstractFormatter(abc.ABC):
    def __init__(self):
        self.opposite_obj = None

    @staticmethod
    @abc.abstractmethod
    def format_model(model):
        pass

    @staticmethod
    @abc.abstractmethod
    def format_tableau(tableau):
        pass
