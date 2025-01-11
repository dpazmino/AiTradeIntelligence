from abc import ABC, abstractmethod
import pandas as pd

class TradingStrategy(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> dict:
        pass

    @abstractmethod
    def get_prompt(self) -> str:
        pass

    def calculate_confidence(self, signals: dict) -> float:
        """Calculate confidence score for the signals"""
        pass
