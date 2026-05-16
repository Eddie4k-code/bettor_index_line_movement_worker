# Concrete implementation using SQLAlchemy
from typing import List

from sqlalchemy.orm import Session
from db.models.odds_api_props_history import OddsAPIPropHistory
from interfaces.odds_api_props_history_interface import OddsApiPropsHistoryRepositoryInterface
from schemas.odds_api_props_history import OddsApiPropsHistorySchema
import logging


logger = logging.getLogger(__name__)


class OddsApiPropsHistoryRepository(OddsApiPropsHistoryRepositoryInterface):
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_all_analyzed_sorted_by_change_time(self) -> List[OddsApiPropsHistorySchema]:
        try:
            records = (
                self.db_session.query(OddsAPIPropHistory)
                .filter(OddsAPIPropHistory.analyzed == True)
                .order_by(OddsAPIPropHistory.change_time.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching analyzed records: {e}")
            raise e
        
        return [OddsApiPropsHistorySchema.from_orm(record) for record in records]
    
