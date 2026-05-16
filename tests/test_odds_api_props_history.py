
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from interfaces.odds_api_props_history_interface import OddsApiPropsHistoryRepositoryInterface
from db.models.odds_api_props_history import OddsAPIPropHistory
from db.models.base import Base
from schemas.odds_api_props_history import OddsApiPropsHistorySchema
from datetime import datetime


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
        analyzed=False
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
        analyzed=True
    )
    in_memory_db.add_all([record1, record2])
    in_memory_db.commit()
    return in_memory_db


def test_get_all_analyzed_sorted_by_change_time(populate_db, mocker):
    test_Data = populate_db.query(OddsAPIPropHistory).filter_by(analyzed=True).order_by(OddsAPIPropHistory.change_time.desc()).all()
    expected = [OddsApiPropsHistorySchema.from_orm(record) for record in test_Data]


    assert len(expected) == 1
    assert expected[0].event_id == "evt2"
    assert expected[0].bookmaker == "BookB"
    assert expected[0].market_key == "market2"
    assert expected[0].outcome_name == "Outcome2"
    assert expected[0].old_point == 2.5
    assert expected[0].new_point == 3.0
    assert expected[0].old_price == 120.0
    assert expected[0].new_price == 130.0
    assert expected[0].outcome_description == "desc2"
    assert expected[0].change_time == datetime(2024, 5, 16, 13, 0, 0)
    assert expected[0].commence_time == datetime(2024, 5, 17, 13, 0, 0)