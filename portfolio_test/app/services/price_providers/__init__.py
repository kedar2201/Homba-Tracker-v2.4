from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PriceProvider(ABC):
    @abstractmethod
    def fetch_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Fetch prices for given symbols.
        Returns a dict: { 'SYMBOL': { 'price': float, 'prev_close': float } }
        """
        pass

    @abstractmethod
    def fetch_history(self, symbol: str, start_date: str) -> Dict[str, float]:
        """
        Fetch historical prices for a given symbol.
        start_date: ISO date YYYY-MM-DD
        Returns a dict: { 'YYYY-MM-DD': float_price }
        """
        pass

    @abstractmethod
    def fetch_history_bulk(self, symbols: List[str], start_date: str) -> Dict[str, Dict[str, float]]:
        """
        Fetch historical prices for multiple symbols at once.
        Returns a dict: { symbol: { 'YYYY-MM-DD': float_price } }
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
