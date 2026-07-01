from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Iterable, List, Tuple

from config.top_movers import TopMoversConfig
from utils.utc import utc_now
from interfaces.prop_history_summarizer_interface import PropHistorySummarizerInterface
from interfaces.prop_movement_summary_interface import PropMovementSummaryRepositoryInterface
from schemas.odds_api_props_history import OddsApiPropsHistorySchema
from schemas.prop_movement_summary import PropMovementSummarySchema

PropKey = Tuple[str, str, str, str, str]


class PropHistorySummarizer(PropHistorySummarizerInterface):
    def __init__(
        self,
        summary_repo: PropMovementSummaryRepositoryInterface,
        config: TopMoversConfig | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self.summary_repo = summary_repo
        self.config = config or TopMoversConfig.from_env()
        self.now_fn = now_fn or utc_now

    def process_batch(
        self, rows: List[OddsApiPropsHistorySchema]
    ) -> List[PropMovementSummarySchema]:
        if not rows:
            return []

        grouped: dict[PropKey, list[OddsApiPropsHistorySchema]] = defaultdict(list)
        for row in rows:
            key = (
                row.event_id,
                row.bookmaker,
                row.market_key,
                row.outcome_name,
                row.outcome_description,
            )
            grouped[key].append(row)

        now = self.now_fn()
        window_start = now - timedelta(hours=self.config.ranking_window_hours)

        return [
            self._aggregate_group(sorted(group_rows, key=lambda r: r.change_time), now, window_start)
            for group_rows in grouped.values()
        ]

    def rank_top_movers(
        self,
        summaries: List[PropMovementSummarySchema],
        as_of: datetime | None = None,
    ) -> None:
        reference_time = as_of or self.now_fn()
        for sport_key, market_key in self._unique_sport_market_pairs(summaries):
            self.summary_repo.rank_top_movers(
                sport_key, market_key, "line", as_of=reference_time
            )
            self.summary_repo.rank_top_movers(
                sport_key, market_key, "price", as_of=reference_time
            )

    def _aggregate_group(
        self,
        rows: List[OddsApiPropsHistorySchema],
        now: datetime,
        window_start: datetime,
    ) -> PropMovementSummarySchema:
        first_row = rows[0]
        latest_row = rows[-1]

        first_point = first_row.old_point
        last_point = latest_row.new_point
        first_price = first_row.old_price
        last_price = latest_row.new_price
        point_move = last_point - first_point
        price_move = last_price - first_price

        window_rows = [row for row in rows if row.change_time >= window_start]
        if window_rows:
            point_move_24h = window_rows[-1].new_point - window_rows[0].old_point
            price_move_24h = window_rows[-1].new_price - window_rows[0].old_price
        else:
            point_move_24h = 0.0
            price_move_24h = 0.0

        sharp_move, sharp_magnitude, sharp_time, sharp_type = self._compute_sharp_move(rows)

        return PropMovementSummarySchema(
            event_id=latest_row.event_id,
            bookmaker=latest_row.bookmaker,
            market_key=latest_row.market_key,
            outcome_name=latest_row.outcome_name,
            outcome_description=latest_row.outcome_description,
            sport_key=latest_row.sport_key,
            commence_time=latest_row.commence_time,
            home_team=latest_row.home_team,
            away_team=latest_row.away_team,
            player_id=latest_row.player_id,
            last_change_time=latest_row.change_time,
            first_point=first_point,
            last_point=last_point,
            point_move=point_move,
            point_move_24h=point_move_24h,
            first_price=first_price,
            last_price=last_price,
            price_move=price_move,
            price_move_24h=price_move_24h,
            move_magnitude=max(abs(point_move), abs(price_move)),
            sharp_move=sharp_move,
            sharp_move_magnitude=sharp_magnitude,
            sharp_move_time=sharp_time,
            sharp_move_type=sharp_type,
            summary_generated_at=now,
        )

    def _compute_sharp_move(
        self, rows: List[OddsApiPropsHistorySchema]
    ) -> tuple[bool, float | None, datetime | None, str | None]:
        best_magnitude = 0.0
        best_time: datetime | None = None
        best_type: str | None = None

        for row in rows:
            if row.change_type == "PointChange":
                magnitude = abs(row.new_point - row.old_point)
            elif row.change_type == "PriceChange":
                magnitude = abs(row.new_price - row.old_price)
            else:
                point_delta = abs(row.new_point - row.old_point)
                price_delta = abs(row.new_price - row.old_price)
                if point_delta >= price_delta:
                    magnitude = point_delta
                else:
                    magnitude = price_delta

            if magnitude > best_magnitude:
                best_magnitude = magnitude
                best_time = row.change_time
                best_type = row.change_type

        if best_type == "PointChange":
            threshold = self.config.min_sharp_line_move
        elif best_type == "PriceChange":
            threshold = self.config.min_sharp_price_move
        else:
            threshold = min(self.config.min_sharp_line_move, self.config.min_sharp_price_move)

        if best_magnitude >= threshold:
            return True, best_magnitude, best_time, best_type

        return False, None, None, None

    @staticmethod
    def _unique_sport_market_pairs(
        summaries: Iterable[PropMovementSummarySchema],
    ) -> set[tuple[str, str]]:
        return {(summary.sport_key, summary.market_key) for summary in summaries}
