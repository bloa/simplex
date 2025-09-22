import abc


class AbstractFormatter(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def format_model(model):
        pass

    @staticmethod
    @abc.abstractmethod
    def format_tableau(tableau):
        pass
