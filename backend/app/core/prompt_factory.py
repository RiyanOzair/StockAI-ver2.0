from typing import List, Dict, Any, Optional


class PromptFactory:
    """Dynamic prompt generation – supports N stocks, financial reports, and bias injection."""

    PERSONA_TEMPLATE = (
        "Your Persona:\n"
        "Name: {name}\n"
        "Type: {trader_type}\n"
        "Description: {description}\n"
        "Risk Tolerance: {risk_tolerance}\n"
    )

    BIAS_INJECTIONS = {
        "herding": (
            "Observation: The market volume is unusually high right now. "
            "Many other traders seem to be {dominant_action}ing. "
            "As a social creature, you feel a strong urge to follow the crowd."
        ),
        "loss_aversion": (
            "Internal State: You are currently running a loss. "
            "The pain of losing money is intense. Be extremely cautious."
        ),
        "overconfidence": (
            "Internal State: You have been winning recently. "
            "You feel confident and might take larger positions."
        ),
        "anchoring": (
            "Internal State: You anchor to earlier prices and are reluctant to "
            "accept that prices have moved far from your reference."
        ),
    }

    # ── helpers ──
    @staticmethod
    def _build_system(available_stocks: List[str]) -> str:
        tickers = ", ".join(available_stocks)
        return (
            f"You are a stock trader in a simulated market with these stocks: {tickers}. "
            "Your goal is to maximize portfolio value. Output strict JSON only."
        )

    @staticmethod
    def _build_market_block(market_state: Dict[str, Any],
                            agent_profile: Dict[str, Any],
                            available_stocks: List[str]) -> str:
        lines = [f"Market Status (Day {market_state.get('day', 1)}, Time {market_state.get('time', '09:30')}):"]
        for sym in available_stocks:
            price = market_state["prices"].get(sym, 0)
            trend = market_state.get("trends", {}).get(sym, "Neutral")
            lines.append(f"  - {sym}: ${price:.2f}  Trend: {trend}")
        lines.append(f"  Market Volume: {market_state.get('volume_level', 'Normal')}")
        lines.append("")
        lines.append("Your Portfolio:")
        lines.append(f"  Cash: ${agent_profile['wallet']['cash']:.2f}")
        holdings_parts = []
        for sym in available_stocks:
            qty = agent_profile["wallet"]["holdings"].get(sym, 0)
            if qty:
                holdings_parts.append(f"{qty} {sym}")
        lines.append(f"  Holdings: {', '.join(holdings_parts) if holdings_parts else 'None'}")
        lines.append(f"  PnL: ${agent_profile.get('pnl', 0):.2f}")

        # Financial report section (if present)
        report = market_state.get("financial_report")
        if report:
            lines.append("")
            lines.append("--- QUARTERLY FINANCIAL REPORT ---")
            for sym, metrics in report.items():
                lines.append(f"  {sym}: Revenue ${metrics.get('revenue', 0):,.0f}, "
                             f"Profit ${metrics.get('profit', 0):,.0f}, "
                             f"Margin {metrics.get('margin', 0):.1%}")
        return "\n".join(lines)

    @staticmethod
    def _build_action_block(news: str, bias_instructions: str,
                            available_stocks: List[str]) -> str:
        stock_choices = " | ".join(f'"{s}"' for s in available_stocks) + " | null"
        return (
            "Based on the news and market state above, decide your next action.\n"
            "Available Actions: Buy (Limit), Sell (Limit), Hold.\n"
            f"\nLatest News:\n{news}\n"
            f"\n{bias_instructions}\n"
            "\nReturn ONLY a JSON object:\n"
            "{\n"
            '  "action": "buy" | "sell" | "hold",\n'
            f'  "stock": {stock_choices},\n'
            '  "quantity": <integer>,\n'
            '  "price": <float>,\n'
            '  "reasoning": "<short explanation>"\n'
            "}"
        )

    # ── main entry point ──
    @staticmethod
    def create_trade_prompt(
        agent_profile: Dict[str, Any],
        market_state: Dict[str, Any],
        active_biases: List[str],
        news: str,
        available_stocks: Optional[List[str]] = None,
    ) -> str:
        if available_stocks is None:
            available_stocks = sorted(market_state.get("prices", {}).keys())

        parts = [PromptFactory._build_system(available_stocks)]

        parts.append(PromptFactory.PERSONA_TEMPLATE.format(
            name=agent_profile.get("name", "Unknown Trader"),
            trader_type=agent_profile.get("type", "Standard"),
            description=agent_profile.get("description", "A regular market participant."),
            risk_tolerance=agent_profile.get("risk_tolerance", "Medium"),
        ))

        parts.append(PromptFactory._build_market_block(market_state, agent_profile, available_stocks))

        bias_texts = []
        for bias_key in active_biases:
            if bias_key in PromptFactory.BIAS_INJECTIONS:
                text = PromptFactory.BIAS_INJECTIONS[bias_key]
                if bias_key == "herding":
                    sentiment = market_state.get("sentiment", "neutral")
                    action_word = {"bullish": "buy", "bearish": "sell"}.get(sentiment, "trad")
                    text = text.format(dominant_action=action_word)
                bias_texts.append(f"*** BEHAVIORAL TRIGGER: {text} ***")

        parts.append(PromptFactory._build_action_block(
            news, "\n".join(bias_texts), available_stocks
        ))
        return "\n\n".join(parts)
