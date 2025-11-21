from strat_base import StrategyBase

class CompStrat(StrategyBase):
    def __init__(self):
        super().__init__()

    def initialize(self) -> None:
        pass

    def execute(self, data: pd.DataFrame) -> None:
        pass

    def on_data(self, data: pd.DataFrame) -> None:
        pass
    