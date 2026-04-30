import logging
from typing import Dict, Any
from backend.app.core.live_market import LiveMarketService
from backend.app.core.india_market import IndiaMarketService

logger = logging.getLogger("core.sentiment")

class MoodEngine:
    def __init__(self):
        self.live_service = LiveMarketService()
        self.india_service = IndiaMarketService()

    async def get_global_sentiment(self) -> Dict[str, Any]:
        """
        Calculate global market sentiment score (-1.0 to 1.0).
        0.0 = Neutral
        > 0.2 = Bullish / High Growth
        < -0.2 = Bearish / Crisis
        """
        try:
            # Fetch US and India data
            us_data = await self.live_service.get_snapshot()
            india_data = await self.india_service.get_summary()

            indices = []
            
            # Extract change percentages from US indices
            for idx in us_data.get("indices", []):
                indices.append(idx.get("change_pct", 0.0))
            
            # Extract change percentages from India indices
            for idx in india_data.get("indices", []):
                indices.append(idx.get("change_pct", 0.0))

            if not indices:
                return self._neutral_response("No data available")

            # Simple weighted average
            avg_change = sum(indices) / len(indices)
            
            # Normalize to -1.0 to 1.0 range
            # Assume 3% move is "maximum" impact for UI purposes
            mood_score = max(-1.0, min(1.0, avg_change / 3.0))
            
            regime = "neutral"
            if mood_score > 0.15:
                regime = "bullish"
            elif mood_score < -0.15:
                regime = "bearish"

            return {
                "mood_score": round(mood_score, 3),
                "avg_change_pct": round(avg_change, 2),
                "regime": regime,
                "timestamp": us_data.get("generated_at"),
                "indices_counted": len(indices)
            }

        except Exception as e:
            logger.error(f"Error calculating global sentiment: {e}")
            return self._neutral_response(str(e))

    def _neutral_response(self, reason: str) -> Dict[str, Any]:
        return {
            "mood_score": 0.0,
            "avg_change_pct": 0.0,
            "regime": "neutral",
            "reason": reason,
            "indices_counted": 0
        }

# Global instance
mood_engine = MoodEngine()
