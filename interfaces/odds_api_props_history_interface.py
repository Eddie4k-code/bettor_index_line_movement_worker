from abc import ABC, abstractmethod
from typing import List
from schemas.odds_api_props_history import OddsApiPropsHistorySchema

class OddsApiPropsHistoryRepositoryInterface(ABC):
    @abstractmethod
    def get_all_analyzed_sorted_by_change_time(self) -> List[OddsApiPropsHistorySchema]:
        pass

    @abstractmethod
    def get_unanalyzed(self, batch_size: int) -> List[OddsApiPropsHistorySchema]:
        pass

    @abstractmethod
    def mark_analyzed(self, ids: List[int]) -> None:
        pass