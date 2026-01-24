# StockAI - Market Simulation Lab

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An agent-based stock market simulation platform that explores the intersection of behavioral finance and artificial intelligence. Watch autonomous trading agents with unique personalities compete, collaborate, and shape market dynamics in real-time simulations.

## ✨ Features

- **🤖 50+ AI Trading Agents** - Autonomous agents with different trading strategies (Conservative, Aggressive, Balanced, Growth-Oriented)
- **📊 Real-Time Analytics** - Interactive Plotly charts showing price movements, volume, and technical indicators
- **🧠 Behavioral Finance** - Agents exhibit real behavioral biases (Herding, Loss Aversion, Overconfidence, Anchoring)
- **💬 BBS Forum** - Agents communicate through a bulletin board system, sharing opinions and sentiment
- **📈 Market Events** - Random economic events that impact stock prices and agent behavior
- **🏆 Leaderboard** - Track top-performing agents and compare strategy effectiveness
- **📤 Export Data** - Download simulation results for further analysis

## 🖥️ Screenshots

### Landing Page
Premium glassmorphism design with animated gradients and feature highlights.

### Simulation Dashboard
Real-time market overview with stock performance charts, agent activities, and key metrics.

### Guidelines Page
Comprehensive documentation for using the platform effectively.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RiyanOzair/StockAI.git
cd StockAI
```

2. Create and activate virtual environment:
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run ui/app.py --server.port 8510
```

5. Open your browser at `http://localhost:8510`

## 📁 Project Structure

```
StockAI/
├── ui/
│   ├── app.py              # Main Streamlit application
│   ├── simulation_engine.py # Backend simulation logic
│   └── favicon.svg         # Custom logo
├── .streamlit/
│   └── config.toml         # Streamlit configuration
├── fig/                    # Architecture diagrams
├── log/                    # Logging utilities
├── prompt/                 # Agent prompts
├── res/                    # Simulation results
├── requirements.txt        # Python dependencies
└── README.md
```

## 🎮 How to Use

1. **Launch the App** - Start the Streamlit server
2. **Read Guidelines** - Click "View Guidelines" to understand the platform
3. **Configure Simulation** - Set parameters (agents, days, volatility, seed)
4. **Run Simulation** - Click "Run Day" to advance trading days
5. **Monitor Dashboard** - Watch real-time updates on Overview tab
6. **Analyze Results** - Use the Analysis tab to compare agent strategies

## 🔧 Configuration

Edit `.streamlit/config.toml` to customize the theme:

```toml
[theme]
primaryColor = "#10b981"
backgroundColor = "#0a0a0f"
secondaryBackgroundColor = "#16161d"
textColor = "#fafafa"
font = "sans serif"
```

## 📊 Agent Strategies

| Strategy | Risk Level | Description |
|----------|------------|-------------|
| 🛡️ Conservative | Low | Prefers stable assets, uses stop-loss orders |
| 🔥 Aggressive | High | Trades on momentum, uses leverage |
| ⚖️ Balanced | Medium | Diversifies, follows fundamental analysis |
| 🚀 Growth-Oriented | High | Focuses on high-growth opportunities |

## 🧠 Behavioral Biases

- **🐑 Herding** - Following crowd behavior
- **😰 Loss Aversion** - Feeling losses more than gains
- **😤 Overconfidence** - Overestimating abilities
- **⚓ Anchoring** - Relying on initial information

## 🛠️ Tech Stack

- **Frontend**: Streamlit, Custom CSS (Glassmorphism)
- **Charts**: Plotly
- **Backend**: Python, Dataclasses
- **Fonts**: Inter, JetBrains Mono

## 📝 License

This project is licensed under the MIT License.

## 👥 Authors

- Riyan Ozair

## 🙏 Acknowledgments

Based on research from "When AI Meets Finance (StockAgent): Large Language Model-based Stock Trading in Simulated Real-world Environments"

---

<p align="center">
  <b>StockAI</b> - Explore the future of AI-driven market simulation
</p>


