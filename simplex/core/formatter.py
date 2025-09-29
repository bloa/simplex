import abc


class AbstractFormatter(abc.ABC):
    def __init__(self):
        self.opposite_obj = None

    @abc.abstractmethod
    def format_section(self, title):
        pass

    @abc.abstractmethod
    def format_step(self, title):
        pass

    @abc.abstractmethod
    def format_action(self, text):
        pass

    @abc.abstractmethod
    def format_info(self, text):
        pass

    @abc.abstractmethod
    def format_decision(self, text):
        pass

    @abc.abstractmethod
    def format_raw_model(self, raw):
        pass

    @abc.abstractmethod
    def format_objective(self, model):
        pass

    @abc.abstractmethod
    def format_model(self, model):
        pass

    @abc.abstractmethod
    def format_tableau(self, tableau):
        pass

    @abc.abstractmethod
    def format_summary(self, summary):
        pass
