from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime

class StrategyBase(ABC):

    def __init__(self, start_date: datetime, end_date: datetime, symbols: list[str], cash: float):

        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        self.cash = cash

        self.parameteres = {

        }


    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def execute(self, data: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def on_data(self, data: pd.DataFrame) -> None:
        pass