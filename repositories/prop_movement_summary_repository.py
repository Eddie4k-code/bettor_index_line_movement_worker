import logging
from datetime import datetime
from typing import Callable, List

from sqlalchemy.orm import Session

from config.top_movers import TopMoversConfig
from db.models.prop_movement_summary import PropMovementSummary
from interfaces.prop_movement_summary_interface import (
    PropMovementSummaryRepositoryInterface,
    TopMoverCategory,
)
from schemas.prop_movement_summary import PropMovementSummarySchema

logger = logging.getLogger(__name__)


class PropMovementSummaryRepository(PropMovementSummaryRepositoryInterface):
    def __init__(
        self,
        db_session: Session,
        config: TopMoversConfig | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self.db_session = db_session
        self.config = config or TopMoversConfig.from_env()
        self.now_fn = now_fn or datetime.utcnow

    def upsert_many(self, summaries: List[PropMovementSummarySchema]) -> None:
        try:
            for summary in summaries:
                self.db_session.merge(self._schema_to_model(summary))
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error upserting prop movement summaries: {e}")
            raise

    def reset_top_mover_flags(
        self,
        sport_key: str,
        market_key: str,
        category: TopMoverCategory,
        *,
        commit: bool = True,
    ) -> None:
        flag_column = self._flag_column(category)
        try:
            (
                self.db_session.query(PropMovementSummary)
                .filter(
                    PropMovementSummary.sport_key == sport_key,
                    PropMovementSummary.market_key == market_key,
                )
                .update({flag_column: False}, synchronize_session=False)
            )
            if commit:
                self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(
                f"Error resetting top mover flags for {sport_key}/{market_key}/{category}: {e}"
            )
            raise

    def rank_top_movers(
        self,
        sport_key: str,
        market_key: str,
        category: TopMoverCategory,
        as_of: datetime | None = None,
    ) -> None:
        reference_time = as_of or self.now_fn()
        move_column, flag_column, min_threshold = self._category_fields(category)

        try:
            self.reset_top_mover_flags(
                sport_key, market_key, category, commit=False
            )

            candidates = (
                self.db_session.query(PropMovementSummary)
                .filter(
                    PropMovementSummary.sport_key == sport_key,
                    PropMovementSummary.market_key == market_key,
                    PropMovementSummary.commence_time > reference_time,
                )
                .all()
            )

            eligible = [
                row
                for row in candidates
                if abs(getattr(row, move_column) or 0) >= min_threshold
            ]
            eligible.sort(key=lambda row: abs(getattr(row, move_column) or 0), reverse=True)

            for row in eligible[: self.config.top_n]:
                setattr(row, flag_column, True)

            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(
                f"Error ranking top movers for {sport_key}/{market_key}/{category}: {e}"
            )
            raise

    def _schema_to_model(self, summary: PropMovementSummarySchema) -> PropMovementSummary:
        return PropMovementSummary(**summary.model_dump())

    def _flag_column(self, category: TopMoverCategory):
        if category == "line":
            return PropMovementSummary.top_line_mover
        if category == "price":
            return PropMovementSummary.top_price_mover
        raise ValueError(f"Unsupported top mover category: {category}")

    def _category_fields(self, category: TopMoverCategory) -> tuple[str, str, float]:
        if category == "line":
            return "point_move_24h", "top_line_mover", self.config.min_line_move_24h
        if category == "price":
            return "price_move_24h", "top_price_mover", self.config.min_price_move_24h
        raise ValueError(f"Unsupported top mover category: {category}")
