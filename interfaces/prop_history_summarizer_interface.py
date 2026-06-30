from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from schemas.odds_api_props_history import OddsApiPropsHistorySchema
from schemas.prop_movement_summary import PropMovementSummarySchema


class PropHistorySummarizerInterface(ABC):
    @abstractmethod
    def process_batch(
        self, rows: List[OddsApiPropsHistorySchema]
    ) -> List[PropMovementSummarySchema]:
        pass

    @abstractmethod
    def rank_top_movers(
        self,
        summaries: List[PropMovementSummarySchema],
        as_of: datetime | None = None,
    ) -> None:
        pass
