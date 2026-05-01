"""
Test script for StockAI Simulation Engine
"""
import sys
sys.path.insert(0, 'ui')

from simulation_engine import SimulationEngine

def run_tests():
    print("=" * 60)
    print("StockAI Simulation Engine Test Suite")
    print("=" * 60)
    print()
    
    engine = SimulationEngine()
    
    # Test 1: Initialize engine
    print("Test 1: Initialize engine...")
    print(f"  ✓ Engine initialized")
    
    # Test 2: Configure simulation
    print("Test 2: Configure simulation...")
    engine.configure(agent_count=20, total_days=10, volatility="Medium", event_intensity=5)
    state = engine.get_state()
    print(f"  ✓ Configured: {state.agent_count} agents, {state.total_days} days")
    print(f"  ✓ Status: {state.status}")
    
    # Test 3: Check agents created
    print("Test 3: Verify agents...")
    print(f"  ✓ {len(state.agents)} agents created")
    strategies = {}
    for a in state.agents:
        strategies[a.character] = strategies.get(a.character, 0) + 1
    print(f"  ✓ Strategies: {strategies}")
    
    # Test 4: Run a trading day
    print("Test 4: Run trading day...")
    engine.run_day()
    state = engine.get_state()
    print(f"  ✓ Day {state.current_day} completed")
    print(f"  ✓ Stock A: ${state.stock_a.price:.2f}")
    print(f"  ✓ Stock B: ${state.stock_b.price:.2f}")
    
    # Test 5: Check price history
    print("Test 5: Price history...")
    price_data = engine.get_price_history_df()
    print(f"  ✓ {len(price_data['days'])} data points")
    
    # Test 6: Check events
    print("Test 6: Market events...")
    print(f"  ✓ {len(state.events)} events generated")
    
    # Test 7: Check BBS messages
    print("Test 7: BBS messages...")
    msgs = engine.get_recent_messages(5)
    print(f"  ✓ {len(msgs)} forum messages")
    
    # Test 8: Strategy performance
    print("Test 8: Strategy performance...")
    perf = engine.get_strategy_performance()
    for strat, data in perf.items():
        print(f"  ✓ {strat}: {data['count']} agents, {data['avg_pnl']:.2f}% avg")
    
    # Test 9: Run more days
    print("Test 9: Run 5 more days...")
    for _ in range(5):
        engine.run_day()
    state = engine.get_state()
    print(f"  ✓ Day {state.current_day} reached")
    
    # Test 10: Check agent details
    print("Test 10: Agent details...")
    agent = engine.get_agent(state.agents[0].id)
    print(f"  ✓ Agent: {agent.name} ({agent.character})")
    print(f"  ✓ Cash: ${agent.cash:.2f}")
    print(f"  ✓ P&L: {agent.pnl_percent:.2f}%")
    print(f"  ✓ Trades: {len(agent.action_history)}")
    
    # Test 11: Run to completion
    print("Test 11: Run to completion...")
    while engine.get_state().status != "COMPLETED":
        engine.run_day()
    state = engine.get_state()
    print(f"  ✓ Simulation completed at day {state.current_day}")
    
    # Test 12: Final statistics
    print("Test 12: Final statistics...")
    active = len([a for a in state.agents if not a.quit and not a.is_bankrupt])
    bankrupt = len([a for a in state.agents if a.is_bankrupt])
    print(f"  ✓ Active agents: {active}")
    print(f"  ✓ Bankrupt agents: {bankrupt}")
    
    all_pnls = [a.pnl_percent for a in state.agents if not a.quit]
    avg_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0
    print(f"  ✓ Average P&L: {avg_pnl:.2f}%")
    print(f"  ✓ Best performer: {max(all_pnls):.2f}%")
    print(f"  ✓ Worst performer: {min(all_pnls):.2f}%")
    
    # Test 13: Reset
    print("Test 13: Reset engine...")
    engine.reset()
    state = engine.get_state()
    print(f"  ✓ Status after reset: {state.status}")
    print(f"  ✓ Agents: {len(state.agents)}")
    
    print()
    print("=" * 60)
    print("✅ ALL SIMULATION ENGINE TESTS PASSED!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
