from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
from typing import Optional, Any

class StrategyBase(ABC):

    def __init__(self, 
            symbols: Optional[list[str]] = None, 
            cash: Optional[float] = None,
            start_date: Optional[datetime] = None, 
            end_date: Optional[datetime] = None):

        self.start_date = start_date
        self.end_date = end_date
        self.symbols = symbols
        self.cash = cash
        self.parameteres = {}

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def execute(self, data: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def on_data(self, data: Any) -> None:
        pass