from datetime import datetime

import pytest

from workers.line_movement_worker import LineMovementWorker
from schemas.odds_api_props_history import OddsApiPropsHistorySchema
from schemas.prop_movement_summary import PropMovementSummarySchema


def _make_history_row(row_id: int) -> OddsApiPropsHistorySchema:
    return OddsApiPropsHistorySchema(
        id=row_id,
        event_id="evt1",
        bookmaker="draftkings",
        market_key="player_points",
        outcome_name="Over",
        outcome_description="LeBron James",
        old_point=24.5,
        new_point=25.0,
        old_price=-110.0,
        new_price=-110.0,
        change_time=datetime(2024, 5, 15, 10, 0, 0),
        commence_time=datetime(2024, 5, 15, 19, 0, 0),
        sport_key="basketball_nba",
        home_team="Lakers",
        away_team="Celtics",
        change_type="PointChange",
        player_id=1,
        analyzed=False,
    )


def _make_summary() -> PropMovementSummarySchema:
    return PropMovementSummarySchema(
        event_id="evt1",
        bookmaker="draftkings",
        market_key="player_points",
        outcome_name="Over",
        outcome_description="LeBron James",
        sport_key="basketball_nba",
        commence_time=datetime(2024, 5, 15, 19, 0, 0),
        home_team="Lakers",
        away_team="Celtics",
        player_id=1,
        last_change_time=datetime(2024, 5, 15, 10, 0, 0),
        first_point=24.5,
        last_point=25.0,
        point_move=0.5,
        point_move_24h=0.5,
        first_price=-110.0,
        last_price=-110.0,
        price_move=0.0,
        price_move_24h=0.0,
        move_magnitude=0.5,
        sharp_move=False,
        summary_generated_at=datetime(2024, 5, 15, 12, 0, 0),
    )


@pytest.fixture
def history_repo(mocker):
    return mocker.Mock()


@pytest.fixture
def summarizer(mocker):
    return mocker.Mock()


@pytest.fixture
def summary_repo(mocker):
    return mocker.Mock()


@pytest.fixture
def worker(history_repo, summarizer, summary_repo):
    return LineMovementWorker(
        history_repo=history_repo,
        summarizer=summarizer,
        summary_repo=summary_repo,
    )


def test_process_batch_does_nothing_when_queue_empty(worker, history_repo, summarizer, summary_repo):
    history_repo.get_unanalyzed.return_value = []

    result = worker.process_batch(batch_size=100)

    assert result is False
    history_repo.get_unanalyzed.assert_called_once_with(100)
    summarizer.process_batch.assert_not_called()
    summary_repo.upsert_many.assert_not_called()
    summarizer.rank_top_movers.assert_not_called()
    history_repo.mark_analyzed.assert_not_called()


def test_process_batch_summarizes_upserts_ranks_and_marks_analyzed(
    worker, history_repo, summarizer, summary_repo
):
    rows = [_make_history_row(1), _make_history_row(2)]
    summary = _make_summary()
    history_repo.get_unanalyzed.return_value = rows
    summarizer.process_batch.return_value = [summary]

    result = worker.process_batch(batch_size=100)

    assert result is True
    history_repo.get_unanalyzed.assert_called_once_with(100)
    summarizer.process_batch.assert_called_once_with(rows)
    summary_repo.upsert_many.assert_called_once_with([summary])
    summarizer.rank_top_movers.assert_called_once_with([summary])
    history_repo.mark_analyzed.assert_called_once_with([1, 2])


def test_process_batch_still_marks_analyzed_when_summaries_empty(
    worker, history_repo, summarizer, summary_repo
):
    rows = [_make_history_row(42)]
    history_repo.get_unanalyzed.return_value = rows
    summarizer.process_batch.return_value = []

    result = worker.process_batch(batch_size=50)

    assert result is True
    summary_repo.upsert_many.assert_not_called()
    summarizer.rank_top_movers.assert_not_called()
    history_repo.mark_analyzed.assert_called_once_with([42])
