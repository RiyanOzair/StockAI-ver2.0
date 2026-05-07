# PRODUCT_VISION.md — Honest Assessment
<!-- Written as a stranger encountering this project for the first time. -->

## Q1. What does this project actually do for a real person?

It lets you build a simulated stock market, populate it with AI agents (LLM-powered and rule-based),
inject macro events (earnings shocks, liquidity crises), and watch what happens. You can replay
sessions, inspect every agent's reasoning, and compare performance across strategies.

It also pulls live US equity data (and optionally Indian market data) so you can compare the
simulation's regime against what's happening in real markets right now.

## Q2. Who would use this and why would they care?

- **Finance/CS students** studying market microstructure, behavioral finance, or multi-agent systems
- **Quantitative researchers** who want to test strategy ideas (mean reversion, momentum) in a
  controlled environment before risking real capital
- **AI/ML engineers** interested in LLM decision-making under uncertainty
- **Educators** who want an interactive tool to demonstrate how markets work

## Q3. What problem does it solve that is not already solved?

Most backtesting tools are code-only (Backtrader, Zipline) and require programming expertise.
StockAI makes it visual, interactive, and accessible. The unique angle is that LLM agents
*explain their decisions* in plain English — you can read "I sold TECH_A because VIX spiked
and my risk model shifted to defensive" rather than staring at a log file.

The combination of simulation + live data comparison + agent explainability in a single UI
is genuinely novel for an academic project.

## Q4. What would make someone come back to use it again?

- Being able to test their own strategy hypothesis quickly ("does mean reversion work in a
  high-volatility regime?") and getting a clear answer with statistical backing
- The replay feature — watching a market unfold with agent decisions annotated is compelling
- Sharing results with classmates or in a research paper

## Q5. What is missing that would make it genuinely valuable?

1. **The "so what" moment is buried.** When a simulation finishes, the user has to manually
   navigate between tabs and charts to piece together what happened. There's no summary that
   says "here is what happened and here is what it means."

2. **The landing page describes features, not outcomes.** A visitor has no idea what they can
   *do* within 5 minutes. The hero copy is generic academic language.

3. **The chatbot is generic.** It doesn't leverage the live simulation state. A user asking
   "which agent is doing best?" should get a data-driven answer, not a generic LLM response.

4. **No pre-built scenarios.** A new visitor has to figure out the configuration themselves.
   There should be one-click "try this" scenarios that demonstrate the platform's value.

## Q6. The one thing that would make someone say "this is actually useful"?

**A post-simulation summary that answers "so what?" in plain English.** When the sim ends,
show: "LLM agents outperformed rule-based agents by 2.3× on Sharpe in a risk-off market.
Agent ALPHA_3 was the best performer because it correctly identified the regime shift on day 8."

That single feature transforms this from "interesting demo" to "useful research tool."

---

## Real Value Already Present (Not Yet Communicated)

1. **What-if analysis with AI agents**: "What happens to my portfolio if an earnings shock hits
   the tech sector?" — answered with agent decisions and explanations
2. **Statistical strategy testing**: Run mean reversion across 5 seeds, get Sharpe/drawdown/win
   rate — before risking real money
3. **Explainable AI decisions**: Read why each agent made each trade, with confidence scores
4. **Session replay**: Watch a market unfold like a flight recorder for a trading session
