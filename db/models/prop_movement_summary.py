from sqlalchemy import Column, String, Float, DateTime, Boolean
from db.models.base import Base

class PropMovementSummary(Base):
    __tablename__ = 'prop_movement_summary'

    # Composite PK
    event_id = Column(String, primary_key=True)
    bookmaker = Column(String, primary_key=True)
    market_key = Column(String, primary_key=True)
    outcome_name = Column(String, primary_key=True)
    outcome_description = Column(String, primary_key=True)

    first_point = Column(Float)
    last_point = Column(Float)
    point_move = Column(Float)
    first_price = Column(Float)
    last_price = Column(Float)
    price_move = Column(Float)
    move_magnitude = Column(Float)
    top_mover = Column(Boolean, default=False)
    sharp_move = Column(Boolean, default=False)
    sharp_move_magnitude = Column(Float, nullable=True)
    sharp_move_time = Column(DateTime, nullable=True)
    sharp_move_type = Column(String, nullable=True)
    summary_generated_at = Column(DateTime)