from abc import ABC, abstractmethod
from typing import List
from schemas.odds_api_props_history import OddsApiPropsHistorySchema

class OddsApiPropsHistoryRepositoryInterface(ABC):
    @abstractmethod
    def get_all_analyzed_sorted_by_change_time(self) -> List[OddsApiPropsHistorySchema]:
        pass