from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class OddsApiPropsHistorySchema(BaseModel):
    id: int
    event_id: str
    bookmaker: str
    market_key: str
    outcome_name: str
    old_point: float
    new_point: float
    old_price: float
    new_price: float
    outcome_description: str
    change_time: datetime
    commence_time: datetime
    sport_key: str
    home_team: str
    away_team: str
    change_type: str
    player_id: Optional[int] = None
    analyzed: bool

    class Config:
        from_attributes = True
