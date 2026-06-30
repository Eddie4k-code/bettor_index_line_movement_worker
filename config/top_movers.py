import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TopMoversConfig:
    top_n: int = 10
    min_line_move_24h: float = 0.5
    min_price_move_24h: float = 10.0
    ranking_window_hours: int = 24
    min_sharp_line_move: float = 0.5
    min_sharp_price_move: float = 15.0

    @classmethod
    def from_env(cls) -> "TopMoversConfig":
        return cls(
            top_n=int(os.getenv("TOP_MOVERS_COUNT", "10")),
            min_line_move_24h=float(os.getenv("TOP_MOVERS_MIN_LINE_MOVE_24H", "0.5")),
            min_price_move_24h=float(os.getenv("TOP_MOVERS_MIN_PRICE_MOVE_24H", "10")),
            ranking_window_hours=int(os.getenv("TOP_MOVERS_RANKING_WINDOW_HOURS", "24")),
            min_sharp_line_move=float(os.getenv("TOP_MOVERS_MIN_SHARP_LINE_MOVE", "0.5")),
            min_sharp_price_move=float(
                os.getenv("TOP_MOVERS_MIN_SHARP_PRICE_MOVE", "15")
            ),
        )
