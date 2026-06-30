from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Literal

from schemas.prop_movement_summary import PropMovementSummarySchema

TopMoverCategory = Literal["line", "price"]


class PropMovementSummaryRepositoryInterface(ABC):
    @abstractmethod
    def upsert_many(self, summaries: List[PropMovementSummarySchema]) -> None:
        pass

    @abstractmethod
    def reset_top_mover_flags(
        self, sport_key: str, market_key: str, category: TopMoverCategory
    ) -> None:
        pass

    @abstractmethod
    def rank_top_movers(
        self,
        sport_key: str,
        market_key: str,
        category: TopMoverCategory,
        as_of: datetime | None = None,
    ) -> None:
        pass
