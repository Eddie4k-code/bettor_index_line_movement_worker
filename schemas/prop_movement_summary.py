from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PropMovementSummarySchema(BaseModel):
    event_id: str
    bookmaker: str
    market_key: str
    outcome_name: str
    outcome_description: str

    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    player_id: Optional[int] = None
    last_change_time: datetime

    first_point: float
    last_point: float
    point_move: float
    point_move_24h: float
    first_price: float
    last_price: float
    price_move: float
    price_move_24h: float
    move_magnitude: float
    top_mover: bool = False
    top_line_mover: bool = False
    top_price_mover: bool = False
    sharp_move: bool = False
    sharp_move_magnitude: Optional[float] = None
    sharp_move_time: Optional[datetime] = None
    sharp_move_type: Optional[str] = None
    summary_generated_at: datetime

    class Config:
        from_attributes = True
