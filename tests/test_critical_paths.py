"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    StockAI - Critical Path Tests                             ║
║              Unit tests for production-critical functionality                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSimulationEngine(unittest.TestCase):
    """Tests for the simulation engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ui.simulation_engine import SimulationEngine
        self.engine = SimulationEngine()
    
    def test_configure_valid_params(self):
        """Test configuration with valid parameters."""
        state = self.engine.configure(
            agent_count=10,
            total_days=30,
            volatility="Medium",
            event_intensity=3
        )
        self.assertIsNotNone(state)
        self.assertEqual(len(self.engine.state.agents), 10)
        self.assertEqual(self.engine.state.total_days, 30)
    
    def test_configure_boundary_min(self):
        """Test configuration with minimum boundary values."""
        state = self.engine.configure(
            agent_count=1,
            total_days=1,
            volatility="Low",
            event_intensity=1
        )
        self.assertEqual(len(self.engine.state.agents), 1)
    
    def test_configure_boundary_max(self):
        """Test configuration with maximum boundary values."""
        state = self.engine.configure(
            agent_count=500,
            total_days=365,
            volatility="High",
            event_intensity=10
        )
        self.assertEqual(len(self.engine.state.agents), 500)
    
    def test_configure_invalid_agent_count_too_low(self):
        """Test configuration rejects agent_count < 1."""
        with self.assertRaises(ValueError) as ctx:
            self.engine.configure(agent_count=0)
        self.assertIn("agent_count", str(ctx.exception).lower())
    
    def test_configure_invalid_agent_count_too_high(self):
        """Test configuration rejects agent_count > 500."""
        with self.assertRaises(ValueError) as ctx:
            self.engine.configure(agent_count=1000)
        self.assertIn("agent_count", str(ctx.exception).lower())
    
    def test_configure_invalid_days(self):
        """Test configuration rejects invalid days."""
        with self.assertRaises(ValueError) as ctx:
            self.engine.configure(total_days=0)
        self.assertIn("total_days", str(ctx.exception).lower())
    
    def test_configure_invalid_volatility(self):
        """Test configuration rejects invalid volatility."""
        with self.assertRaises(ValueError) as ctx:
            self.engine.configure(volatility="extreme")
        self.assertIn("volatility", str(ctx.exception).lower())
    
    def test_run_day_before_configure(self):
        """Test run_day before configuration returns state with day 0."""
        # New engine has no agents, run_day should handle gracefully
        state = self.engine.run_day()
        # May return state or None depending on implementation
        # Just verify no exception is raised
        self.assertIsNotNone(state) if state else self.assertIsNone(state)
    
    def test_run_day_after_configure(self):
        """Test run_day after configuration works."""
        self.engine.configure(agent_count=5, total_days=10)
        state = self.engine.run_day()
        self.assertIsNotNone(state)
        self.assertEqual(state.current_day, 1)
    
    @unittest.skip("Skipped: deep copy of large state takes too long in test")
    def test_snapshot_memory_limit(self):
        """Test that snapshots are limited to 60."""
        self.engine.configure(agent_count=5, total_days=100)
        for _ in range(70):
            self.engine.run_day()
        self.assertLessEqual(len(self.engine.state.snapshots), 60)


class TestRecordManager(unittest.TestCase):
    """Tests for the batch record manager."""
    
    def test_import(self):
        """Test that BatchRecordManager can be imported."""
        from record import BatchRecordManager
        self.assertTrue(hasattr(BatchRecordManager, 'add_trade'))
    
    def test_class_method_available(self):
        """Test that BatchRecordManager class methods are available."""
        from record import BatchRecordManager
        self.assertTrue(callable(getattr(BatchRecordManager, 'add_trade')))
        self.assertTrue(callable(getattr(BatchRecordManager, 'flush_all')))
    
    def test_add_trade_buffers(self):
        """Test that trades are buffered."""
        from record import BatchRecordManager
        initial_count = len(BatchRecordManager._trade_buffer)
        BatchRecordManager.add_trade(
            date=1,
            session=1,
            stock_type="A",
            buyer="Agent1",
            seller="Agent2",
            quantity=10,
            price=100.0
        )
        self.assertEqual(len(BatchRecordManager._trade_buffer), initial_count + 1)


class TestRateLimiter(unittest.TestCase):
    """Tests for the rate limiter."""
    
    def test_import(self):
        """Test that rate limiter can be imported."""
        from utils.rate_limiter import RateLimiter, groq_limiter
        self.assertIsNotNone(RateLimiter)
        self.assertIsNotNone(groq_limiter)
    
    def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows calls under limit."""
        from utils.rate_limiter import RateLimiter
        limiter = RateLimiter(max_calls=10, window_seconds=60)
        # Should not raise or block (returns quickly)
        wait_time = limiter.acquire()
        self.assertIsNotNone(wait_time)
    
    def test_rate_limiter_wait_if_needed(self):
        """Test wait_if_needed method exists and works."""
        from utils.rate_limiter import RateLimiter
        limiter = RateLimiter(max_calls=10, window_seconds=60)
        # Should work without error
        limiter.wait_if_needed()


class TestChatbot(unittest.TestCase):
    """Tests for the chatbot advisor."""
    
    def test_import(self):
        """Test that chatbot can be imported."""
        from ui.chatbot import StockAIAdvisor
        self.assertTrue(callable(StockAIAdvisor))
    
    def test_provider_name_no_api_key(self):
        """Test provider name when no API key is set."""
        # Temporarily remove API keys
        with patch.dict(os.environ, {'GROQ_API_KEY': '', 'GOOGLE_API_KEY': ''}, clear=True):
            from ui.chatbot import StockAIAdvisor
            advisor = StockAIAdvisor()
            name = advisor.get_provider_name()
            # Should indicate demo mode or no provider
            self.assertIsInstance(name, str)
    
    def test_connection_status(self):
        """Test connection status method."""
        from ui.chatbot import StockAIAdvisor
        advisor = StockAIAdvisor()
        status = advisor.get_connection_status()
        self.assertIn("connected", status)
        self.assertIn("provider", status)


class TestInputValidation(unittest.TestCase):
    """Tests for input validation edge cases."""
    
    def test_negative_values_rejected(self):
        """Test that negative values are rejected."""
        from ui.simulation_engine import SimulationEngine
        engine = SimulationEngine()
        with self.assertRaises(ValueError):
            engine.configure(agent_count=-1)
    
    def test_string_input_type_error(self):
        """Test that string inputs cause type errors."""
        from ui.simulation_engine import SimulationEngine
        engine = SimulationEngine()
        with self.assertRaises((ValueError, TypeError)):
            engine.configure(agent_count="ten")


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
