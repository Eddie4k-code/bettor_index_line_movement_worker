import logging
import time

from analyzers.prop_history_summarizer import PropHistorySummarizer
from config.top_movers import TopMoversConfig
from db.db import engine, get_db
from db.models.base import Base
from repositories.odds_api_props_history_repository import OddsApiPropsHistoryRepository
from repositories.prop_movement_summary_repository import PropMovementSummaryRepository
from workers.line_movement_worker import LineMovementWorker

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

POLL_INTERVAL_SECONDS = 10
BATCH_SIZE = 100


def main():
    Base.metadata.create_all(bind=engine)
    config = TopMoversConfig.from_env()

    with get_db() as db_session:
        history_repo = OddsApiPropsHistoryRepository(db_session)
        summary_repo = PropMovementSummaryRepository(db_session, config=config)
        summarizer = PropHistorySummarizer(summary_repo=summary_repo, config=config)
        worker = LineMovementWorker(
            history_repo=history_repo,
            summarizer=summarizer,
            summary_repo=summary_repo,
        )

        while True:
            worker.process_batch(batch_size=BATCH_SIZE)
            time.sleep(POLL_INTERVAL_SECONDS)
            logger.info(
                "Worker cycle completed, sleeping for %s seconds...",
                POLL_INTERVAL_SECONDS,
            )


main()
