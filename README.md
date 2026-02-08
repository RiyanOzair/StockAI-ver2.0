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

4. Set up FREE LLM API Key (Groq recommended):
   - Go to https://console.groq.com and create a free account
   - Click "API Keys" and generate a new key
   - Copy `.env.example` to `.env` and paste your key:
     ```env
     GROQ_API_KEY=your_groq_api_key_here
     ```
   - (Optional) For Google Gemini, get a key at https://aistudio.google.com

5. Run the application:
```bash
streamlit run ui/app.py --server.port 8510
```

6. Open your browser at `http://localhost:8510`

**Default LLM:** Llama 3.3 70B (free via Groq)

**Security:** Never share your `.env` file or API keys publicly. `.env` is gitignored by default.

## 🚢 Deployment

### Streamlit Cloud (Recommended - Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add secrets in the dashboard (Settings → Secrets):
   ```toml
   GROQ_API_KEY = "your_key"
   GOOGLE_API_KEY = "your_key"
   ```
5. Deploy!

### Docker

```bash
# Build the image
docker build -t stockai .

# Run the container
docker run -p 8510:8510 --env-file .env stockai
```

### Manual Server Deployment

```bash
# Install on server
pip install -r requirements.txt

# Run with production settings
streamlit run ui/app.py --server.port 8510 --server.address 0.0.0.0 --server.headless true
```

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
- Nabeel Rizwan
- Samiullah

## 🙏 Acknowledgments

Based on research from "When AI Meets Finance (StockAgent): Large Language Model-based Stock Trading in Simulated Real-world Environments"

- **Reffernced Repository**: [MingyuJ666/Stockagent](https://github.com/MingyuJ666/Stockagent)
- **Paper**: [arXiv:2407.18957](https://arxiv.org/pdf/2407.18957)

---

<p align="center">
  <b>StockAI</b> - Explore the future of AI-driven market simulation
</p>


