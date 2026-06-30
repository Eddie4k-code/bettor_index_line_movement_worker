import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.top_movers import TopMoversConfig
from db.models.base import Base
from db.models.prop_movement_summary import PropMovementSummary
from repositories.prop_movement_summary_repository import PropMovementSummaryRepository
from schemas.prop_movement_summary import PropMovementSummarySchema


@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def reference_time():
    return datetime(2024, 5, 15, 12, 0, 0)


@pytest.fixture
def repo(in_memory_db, reference_time):
    config = TopMoversConfig(top_n=10, min_line_move_24h=0.5, min_price_move_24h=10)
    return PropMovementSummaryRepository(
        in_memory_db,
        config=config,
        now_fn=lambda: reference_time,
    )


def _make_summary(
    *,
    event_id: str,
    bookmaker: str = "draftkings",
    market_key: str = "player_points",
    sport_key: str = "basketball_nba",
    outcome_name: str = "Over",
    outcome_description: str = "LeBron James",
    point_move_24h: float = 1.0,
    price_move_24h: float = 20.0,
    commence_time: datetime | None = None,
    reference_time: datetime | None = None,
) -> PropMovementSummarySchema:
    ref = reference_time or datetime(2024, 5, 15, 12, 0, 0)
    game_time = commence_time or ref + timedelta(hours=6)
    generated_at = ref
    return PropMovementSummarySchema(
        event_id=event_id,
        bookmaker=bookmaker,
        market_key=market_key,
        outcome_name=outcome_name,
        outcome_description=outcome_description,
        sport_key=sport_key,
        commence_time=game_time,
        home_team="Lakers",
        away_team="Celtics",
        player_id=1,
        last_change_time=ref,
        first_point=24.5,
        last_point=24.5 + point_move_24h,
        point_move=point_move_24h,
        point_move_24h=point_move_24h,
        first_price=-110.0,
        last_price=-110.0 - price_move_24h,
        price_move=price_move_24h,
        price_move_24h=price_move_24h,
        move_magnitude=max(abs(point_move_24h), abs(price_move_24h)),
        summary_generated_at=generated_at,
    )


def test_upsert_many_inserts_new_row(repo, in_memory_db):
    summary = _make_summary(event_id="evt1")

    repo.upsert_many([summary])

    row = in_memory_db.get(
        PropMovementSummary,
        ("evt1", "draftkings", "player_points", "Over", "LeBron James"),
    )
    assert row is not None
    assert row.point_move_24h == 1.0
    assert row.price_move_24h == 20.0


def test_upsert_many_updates_existing_row(repo, in_memory_db):
    original = _make_summary(event_id="evt1", point_move_24h=1.0)
    updated = _make_summary(event_id="evt1", point_move_24h=2.5)

    repo.upsert_many([original])
    repo.upsert_many([updated])

    rows = in_memory_db.query(PropMovementSummary).all()
    assert len(rows) == 1
    assert rows[0].point_move_24h == 2.5
    assert rows[0].last_point == 27.0


def test_reset_top_mover_flags_clears_line_flags(repo, in_memory_db, reference_time):
    summaries = [
        _make_summary(
            event_id=f"evt{i}",
            point_move_24h=float(i),
            reference_time=reference_time,
        )
        for i in range(3)
    ]
    repo.upsert_many(summaries)
    in_memory_db.query(PropMovementSummary).update({PropMovementSummary.top_line_mover: True})
    in_memory_db.commit()

    repo.reset_top_mover_flags("basketball_nba", "player_points", "line")

    flagged = (
        in_memory_db.query(PropMovementSummary)
        .filter(PropMovementSummary.top_line_mover.is_(True))
        .count()
    )
    assert flagged == 0


def test_reset_top_mover_flags_clears_price_flags_only(repo, in_memory_db, reference_time):
    summaries = [
        _make_summary(
            event_id=f"evt{i}",
            reference_time=reference_time,
        )
        for i in range(2)
    ]
    repo.upsert_many(summaries)
    in_memory_db.query(PropMovementSummary).update(
        {
            PropMovementSummary.top_line_mover: True,
            PropMovementSummary.top_price_mover: True,
        }
    )
    in_memory_db.commit()

    repo.reset_top_mover_flags("basketball_nba", "player_points", "price")

    rows = in_memory_db.query(PropMovementSummary).all()
    assert all(row.top_line_mover for row in rows)
    assert not any(row.top_price_mover for row in rows)


def test_rank_top_movers_line_flags_top_n(repo, in_memory_db, reference_time):
    summaries = [
        _make_summary(
            event_id=f"evt{i}",
            point_move_24h=0.5 + (i * 0.1),
            reference_time=reference_time,
        )
        for i in range(15)
    ]
    repo.upsert_many(summaries)

    repo.rank_top_movers("basketball_nba", "player_points", "line")

    flagged = (
        in_memory_db.query(PropMovementSummary)
        .filter(PropMovementSummary.top_line_mover.is_(True))
        .order_by(PropMovementSummary.point_move_24h.desc())
        .all()
    )
    assert len(flagged) == 10
    assert flagged[0].event_id == "evt14"
    assert flagged[-1].event_id == "evt5"


def test_rank_top_movers_price_independent_from_line(repo, in_memory_db, reference_time):
    summary = _make_summary(
        event_id="evt1",
        point_move_24h=0.4,
        price_move_24h=25.0,
        reference_time=reference_time,
    )
    repo.upsert_many([summary])

    repo.rank_top_movers("basketball_nba", "player_points", "line")
    repo.rank_top_movers("basketball_nba", "player_points", "price")

    row = in_memory_db.query(PropMovementSummary).one()
    assert row.top_line_mover is False
    assert row.top_price_mover is True


def test_rank_top_movers_skips_past_games(repo, in_memory_db, reference_time):
    upcoming = _make_summary(
        event_id="upcoming",
        point_move_24h=2.0,
        reference_time=reference_time,
    )
    past = _make_summary(
        event_id="past",
        point_move_24h=5.0,
        commence_time=reference_time - timedelta(hours=1),
        reference_time=reference_time,
    )
    repo.upsert_many([upcoming, past])

    repo.rank_top_movers("basketball_nba", "player_points", "line")

    upcoming_row = in_memory_db.get(
        PropMovementSummary,
        ("upcoming", "draftkings", "player_points", "Over", "LeBron James"),
    )
    past_row = in_memory_db.get(
        PropMovementSummary,
        ("past", "draftkings", "player_points", "Over", "LeBron James"),
    )
    assert upcoming_row.top_line_mover is True
    assert past_row.top_line_mover is False
