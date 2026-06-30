from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from analyzers.prop_history_summarizer import PropHistorySummarizer
from config.top_movers import TopMoversConfig
from schemas.odds_api_props_history import OddsApiPropsHistorySchema
from schemas.prop_movement_summary import PropMovementSummarySchema


@pytest.fixture
def reference_time():
    return datetime(2024, 5, 15, 12, 0, 0)


@pytest.fixture
def config():
    return TopMoversConfig(
        top_n=10,
        min_line_move_24h=0.5,
        min_price_move_24h=10.0,
        ranking_window_hours=24,
        min_sharp_line_move=0.5,
        min_sharp_price_move=15.0,
    )


@pytest.fixture
def summary_repo():
    return Mock()


@pytest.fixture
def summarizer(summary_repo, config, reference_time):
    return PropHistorySummarizer(
        summary_repo=summary_repo,
        config=config,
        now_fn=lambda: reference_time,
    )


def _make_history_row(
    *,
    row_id: int,
    event_id: str = "evt1",
    bookmaker: str = "draftkings",
    market_key: str = "player_points",
    outcome_name: str = "Over",
    outcome_description: str = "LeBron James",
    old_point: float = 24.5,
    new_point: float = 25.0,
    old_price: float = -110.0,
    new_price: float = -110.0,
    change_time: datetime,
    change_type: str = "PointChange",
    sport_key: str = "basketball_nba",
    commence_time: datetime | None = None,
    reference_time: datetime | None = None,
) -> OddsApiPropsHistorySchema:
    ref = reference_time or datetime(2024, 5, 15, 12, 0, 0)
    return OddsApiPropsHistorySchema(
        id=row_id,
        event_id=event_id,
        bookmaker=bookmaker,
        market_key=market_key,
        outcome_name=outcome_name,
        outcome_description=outcome_description,
        old_point=old_point,
        new_point=new_point,
        old_price=old_price,
        new_price=new_price,
        change_time=change_time,
        commence_time=commence_time or ref + timedelta(hours=6),
        sport_key=sport_key,
        home_team="Lakers",
        away_team="Celtics",
        change_type=change_type,
        player_id=1,
        analyzed=False,
    )


def test_process_batch_empty_returns_empty(summarizer):
    assert summarizer.process_batch([]) == []


def test_process_batch_aggregates_line_moves(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=25.0,
            change_time=reference_time - timedelta(hours=3),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            old_point=25.0,
            new_point=26.0,
            change_time=reference_time - timedelta(hours=2),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=3,
            old_point=26.0,
            new_point=26.5,
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summaries = summarizer.process_batch(rows)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.first_point == 24.5
    assert summary.last_point == 26.5
    assert summary.point_move == 2.0
    assert summary.point_move_24h == 2.0


def test_process_batch_aggregates_price_moves(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=24.5,
            old_price=-110.0,
            new_price=-115.0,
            change_type="PriceChange",
            change_time=reference_time - timedelta(hours=2),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            old_point=24.5,
            new_point=24.5,
            old_price=-115.0,
            new_price=-130.0,
            change_type="PriceChange",
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summaries = summarizer.process_batch(rows)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.first_price == -110.0
    assert summary.last_price == -130.0
    assert summary.price_move == -20.0
    assert summary.price_move_24h == -20.0


def test_process_batch_24h_move_excludes_older_rows(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=25.0,
            change_time=reference_time - timedelta(hours=48),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            old_point=25.0,
            new_point=26.0,
            change_time=reference_time - timedelta(hours=12),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=3,
            old_point=26.0,
            new_point=26.5,
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summary = summarizer.process_batch(rows)[0]

    assert summary.point_move == 2.0
    assert summary.point_move_24h == 1.5


def test_process_batch_flags_sharp_move(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=25.0,
            change_time=reference_time - timedelta(hours=2),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            old_point=25.0,
            new_point=26.5,
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summary = summarizer.process_batch(rows)[0]

    assert summary.sharp_move is True
    assert summary.sharp_move_magnitude == 1.5
    assert summary.sharp_move_type == "PointChange"
    assert summary.sharp_move_time == reference_time - timedelta(hours=1)


def test_process_batch_no_sharp_move_below_threshold(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=24.7,
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summary = summarizer.process_batch(rows)[0]

    assert summary.sharp_move is False
    assert summary.sharp_move_magnitude is None


def test_process_batch_groups_by_prop_key(summarizer, reference_time):
    rows = [
        _make_history_row(
            row_id=1,
            event_id="evt1",
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            event_id="evt2",
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summaries = summarizer.process_batch(rows)

    assert len(summaries) == 2
    assert {s.event_id for s in summaries} == {"evt1", "evt2"}


def test_process_batch_copies_display_metadata_from_latest_row(
    summarizer, reference_time
):
    rows = [
        _make_history_row(
            row_id=1,
            old_point=24.5,
            new_point=25.0,
            change_time=reference_time - timedelta(hours=2),
            reference_time=reference_time,
        ),
        _make_history_row(
            row_id=2,
            old_point=25.0,
            new_point=26.0,
            change_time=reference_time - timedelta(hours=1),
            reference_time=reference_time,
        ),
    ]

    summary = summarizer.process_batch(rows)[0]

    assert summary.sport_key == "basketball_nba"
    assert summary.home_team == "Lakers"
    assert summary.away_team == "Celtics"
    assert summary.player_id == 1
    assert summary.last_change_time == reference_time - timedelta(hours=1)
    assert summary.summary_generated_at == reference_time


def test_rank_top_movers_delegates_to_summary_repo(
    summarizer, summary_repo, reference_time
):
    summaries = [
        PropMovementSummarySchema(
            event_id="evt1",
            bookmaker="draftkings",
            market_key="player_points",
            outcome_name="Over",
            outcome_description="LeBron James",
            sport_key="basketball_nba",
            commence_time=reference_time + timedelta(hours=6),
            home_team="Lakers",
            away_team="Celtics",
            player_id=1,
            last_change_time=reference_time,
            first_point=24.5,
            last_point=26.5,
            point_move=2.0,
            point_move_24h=2.0,
            first_price=-110.0,
            last_price=-130.0,
            price_move=-20.0,
            price_move_24h=-20.0,
            move_magnitude=20.0,
            summary_generated_at=reference_time,
        ),
        PropMovementSummarySchema(
            event_id="evt2",
            bookmaker="draftkings",
            market_key="player_rebounds",
            outcome_name="Over",
            outcome_description="Anthony Davis",
            sport_key="basketball_nba",
            commence_time=reference_time + timedelta(hours=6),
            home_team="Lakers",
            away_team="Celtics",
            player_id=2,
            last_change_time=reference_time,
            first_point=10.5,
            last_point=11.5,
            point_move=1.0,
            point_move_24h=1.0,
            first_price=-110.0,
            last_price=-120.0,
            price_move=-10.0,
            price_move_24h=-10.0,
            move_magnitude=10.0,
            summary_generated_at=reference_time,
        ),
    ]

    summarizer.rank_top_movers(summaries)

    assert summary_repo.rank_top_movers.call_count == 4
    summary_repo.rank_top_movers.assert_any_call(
        "basketball_nba", "player_points", "line", as_of=reference_time
    )
    summary_repo.rank_top_movers.assert_any_call(
        "basketball_nba", "player_points", "price", as_of=reference_time
    )
    summary_repo.rank_top_movers.assert_any_call(
        "basketball_nba", "player_rebounds", "line", as_of=reference_time
    )
    summary_repo.rank_top_movers.assert_any_call(
        "basketball_nba", "player_rebounds", "price", as_of=reference_time
    )
