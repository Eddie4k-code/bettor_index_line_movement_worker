
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.odds_api_props_history import OddsAPIPropHistory
from db.models.base import Base
from datetime import datetime
from repositories.odds_api_props_history_repository import OddsApiPropsHistoryRepository


@pytest.fixture(scope="function")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def repo(in_memory_db):
    return OddsApiPropsHistoryRepository(in_memory_db)


@pytest.fixture(scope="function")
def populate_db(in_memory_db):
    record1 = OddsAPIPropHistory(
        event_id="evt1",
        bookmaker="BookA",
        market_key="market1",
        outcome_name="Outcome1",
        old_point=1.5,
        new_point=2.0,
        old_price=100.0,
        new_price=110.0,
        outcome_description="desc1",
        change_time=datetime(2024, 5, 15, 12, 0, 0),
        commence_time=datetime(2024, 5, 16, 12, 0, 0),
        sport_key="sport1",
        home_team="TeamA",
        away_team="TeamB",
        change_type="PointChange",
        player_id=None,
        analyzed=False,
    )
    record2 = OddsAPIPropHistory(
        event_id="evt2",
        bookmaker="BookB",
        market_key="market2",
        outcome_name="Outcome2",
        old_point=2.5,
        new_point=3.0,
        old_price=120.0,
        new_price=130.0,
        outcome_description="desc2",
        change_time=datetime(2024, 5, 16, 13, 0, 0),
        commence_time=datetime(2024, 5, 17, 13, 0, 0),
        sport_key="sport2",
        home_team="TeamC",
        away_team="TeamD",
        change_type="PriceChange",
        player_id=42,
        analyzed=True,
    )
    in_memory_db.add_all([record1, record2])
    in_memory_db.commit()
    return in_memory_db


def test_get_all_analyzed_sorted_by_change_time(repo, populate_db):
    results = repo.get_all_analyzed_sorted_by_change_time()

    assert len(results) == 1
    assert results[0].event_id == "evt2"
    assert results[0].bookmaker == "BookB"
    assert results[0].market_key == "market2"
    assert results[0].outcome_name == "Outcome2"
    assert results[0].old_point == 2.5
    assert results[0].new_point == 3.0
    assert results[0].old_price == 120.0
    assert results[0].new_price == 130.0
    assert results[0].outcome_description == "desc2"
    assert results[0].change_time == datetime(2024, 5, 16, 13, 0, 0)
    assert results[0].commence_time == datetime(2024, 5, 17, 13, 0, 0)
    assert results[0].analyzed is True


def test_get_unanalyzed_returns_oldest_first(repo, populate_db):
    record3 = OddsAPIPropHistory(
        event_id="evt3",
        bookmaker="BookC",
        market_key="market3",
        outcome_name="Outcome3",
        old_point=3.5,
        new_point=4.0,
        old_price=140.0,
        new_price=150.0,
        outcome_description="desc3",
        change_time=datetime(2024, 5, 14, 10, 0, 0),
        commence_time=datetime(2024, 5, 15, 10, 0, 0),
        sport_key="sport3",
        home_team="TeamE",
        away_team="TeamF",
        change_type="PointChange",
        player_id=None,
        analyzed=False,
    )
    populate_db.add(record3)
    populate_db.commit()

    results = repo.get_unanalyzed(batch_size=10)

    assert len(results) == 2
    assert results[0].event_id == "evt3"
    assert results[1].event_id == "evt1"
    assert all(not row.analyzed for row in results)


def test_get_unanalyzed_respects_batch_size(repo, populate_db):
    record3 = OddsAPIPropHistory(
        event_id="evt3",
        bookmaker="BookC",
        market_key="market3",
        outcome_name="Outcome3",
        old_point=3.5,
        new_point=4.0,
        old_price=140.0,
        new_price=150.0,
        outcome_description="desc3",
        change_time=datetime(2024, 5, 14, 10, 0, 0),
        commence_time=datetime(2024, 5, 15, 10, 0, 0),
        sport_key="sport3",
        home_team="TeamE",
        away_team="TeamF",
        change_type="PointChange",
        player_id=None,
        analyzed=False,
    )
    populate_db.add(record3)
    populate_db.commit()

    results = repo.get_unanalyzed(batch_size=1)

    assert len(results) == 1
    assert results[0].event_id == "evt3"


def test_get_unanalyzed_returns_empty_when_all_analyzed(repo, populate_db):
    unanalyzed = populate_db.query(OddsAPIPropHistory).filter_by(analyzed=False).all()
    for row in unanalyzed:
        row.analyzed = True
    populate_db.commit()

    results = repo.get_unanalyzed(batch_size=10)

    assert results == []


def test_mark_analyzed_updates_rows(repo, populate_db):
    unanalyzed = repo.get_unanalyzed(batch_size=10)
    ids = [row.id for row in unanalyzed]

    repo.mark_analyzed(ids)

    remaining = repo.get_unanalyzed(batch_size=10)
    assert remaining == []

    analyzed = repo.get_all_analyzed_sorted_by_change_time()
    assert len(analyzed) == 2
    analyzed_ids = {row.id for row in analyzed}
    assert set(ids).issubset(analyzed_ids)


def test_mark_analyzed_noop_for_empty_ids(repo, populate_db):
    repo.mark_analyzed([])

    results = repo.get_unanalyzed(batch_size=10)
    assert len(results) == 1
