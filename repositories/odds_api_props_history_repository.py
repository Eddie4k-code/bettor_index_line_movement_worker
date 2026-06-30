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

    def get_unanalyzed(self, batch_size: int) -> List[OddsApiPropsHistorySchema]:
        try:
            records = (
                self.db_session.query(OddsAPIPropHistory)
                .filter(OddsAPIPropHistory.analyzed == False)
                .order_by(OddsAPIPropHistory.change_time.asc())
                .limit(batch_size)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching unanalyzed records: {e}")
            raise e

        return [OddsApiPropsHistorySchema.from_orm(record) for record in records]

    def mark_analyzed(self, ids: List[int]) -> None:
        if not ids:
            return
        try:
            (
                self.db_session.query(OddsAPIPropHistory)
                .filter(OddsAPIPropHistory.id.in_(ids))
                .update({"analyzed": True}, synchronize_session=False)
            )
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error marking records as analyzed: {e}")
            raise

