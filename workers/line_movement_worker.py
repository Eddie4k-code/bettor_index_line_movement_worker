import logging
from typing import List

from interfaces.line_movement_worker_interface import LineMovementWorkerInterface
from interfaces.odds_api_props_history_interface import OddsApiPropsHistoryRepositoryInterface
from interfaces.prop_history_summarizer_interface import PropHistorySummarizerInterface
from interfaces.prop_movement_summary_interface import PropMovementSummaryRepositoryInterface
from schemas.odds_api_props_history import OddsApiPropsHistorySchema

logger = logging.getLogger(__name__)


class LineMovementWorker(LineMovementWorkerInterface):
    def __init__(
        self,
        history_repo: OddsApiPropsHistoryRepositoryInterface,
        summarizer: PropHistorySummarizerInterface,
        summary_repo: PropMovementSummaryRepositoryInterface,
    ):
        self.history_repo = history_repo
        self.summarizer = summarizer
        self.summary_repo = summary_repo

    def process_batch(self, batch_size: int = 100) -> bool:
        rows: List[OddsApiPropsHistorySchema] = self.history_repo.get_unanalyzed(
            batch_size
        )
        if not rows:
            return False

        logger.info("Processing %s unanalyzed prop history rows", len(rows))

        summaries = self.summarizer.process_batch(rows)
        if summaries:
            self.summary_repo.upsert_many(summaries)
            self.summarizer.rank_top_movers(summaries)

        self.history_repo.mark_analyzed([row.id for row in rows])
        return True
