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

    async def get_market_briefing(self) -> Dict[str, Any]:
        """
        Generate a 2-3 sentence strategic briefing based on current sentiment and movers.
        """
        sentiment = await self.get_global_sentiment()
        
        # If no real data, return a generic one
        if sentiment.get("indices_counted", 0) == 0:
            return {"briefing": "Systems are currently recalibrating. Global market pulse is neutral."}

        prompt = f"""
        Generate a professional, high-impact 2-sentence market briefing for a researcher.
        Current Market Regime: {sentiment['regime'].upper()}
        Mood Score: {sentiment['mood_score']}
        Average Change: {sentiment['avg_change_pct']}%
        
        Tone: Cyberpunk, precise, authoritative (like a mission briefing).
        Format: JSON with key "briefing".
        """
        
        try:
            from backend.app.core.llm_provider import LLMFactory
            provider = LLMFactory.create_provider()
            
            # Use Mock briefing if in mock mode
            if hasattr(provider, 'generate'):
                response_str = provider.generate(prompt, system_message="You are the Lead Market Strategist AI.")
                import json
                response_data = json.loads(response_str)
                return {"briefing": response_data.get("briefing", "Briefing unavailable.")}
        except Exception as e:
            logger.error(f"Failed to generate briefing: {e}")
            
        # Fallback briefings
        fallbacks = {
            "bullish": "Broad market indicators are flashing emerald. Momentum is deep in the growth layer; execute aggressive positioning.",
            "bearish": "Warning: Crisis regime detected. Systemic volatility is surging. Pivot to defensive hedges and monitor liquidity traps.",
            "neutral": "Markets are tracking in a tight range. Pulse is stable but low-volume. Maintain research posture."
        }
        return {"briefing": fallbacks.get(sentiment['regime'], "Maintain research posture.")}

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
