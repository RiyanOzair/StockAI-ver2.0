# StockAI v2.0: Major Project Report (Final Draft - Phase 2)

## 3. Requirement Analysis

### 3.1 Hardware Requirements
The high-fidelity nature of the StockAI simulation, combined with the computational demands of Large Language Model (LLM) integration, necessitates a robust hardware environment.

- **Processor (CPU)**: Minimum Quad-core 2.5 GHz (e.g., Intel i5/i7 or AMD Ryzen 5/7). Multi-threading is essential for the concurrent execution of the Simulation Loop and Agent Reasoning engines.
- **Memory (RAM)**: 8GB DDR4 minimum (16GB recommended). The system maintains a large in-memory state for the Live Tape and order book; additionally, LLM context windows can be memory-intensive.
- **Storage**: 500MB of free space for the core application, plus additional space for SQLite research databases (Run logs can exceed several hundred MB for long simulations).
- **Network**: High-speed internet connection required for live market proxy ingestion and remote LLM API calls (Groq/OpenAI).

### 3.2 Software Requirements
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS Monterey+.
- **Language**: Python 3.9+ (utilizing type hinting and async concurrency).
- **Framework**: FastAPI (Asynchronous REST API) and Uvicorn.
- **Database**: SQLite 3 (Persistent storage) and custom In-memory buffers.
- **Frontend**: Standard Web Browser (Chrome/Edge/Firefox) with ES6 support.
- **Libraries**: Pydantic (Validation), HTTPX (API calls), Chart.js (Visualization).

### 3.3 Software Requirement Specification (SRS)
#### 3.3.1 Functional Requirements
1. **Simulation Control**: User must be able to start, pause, resume, and stop the market kernel.
2. **Agent Management**: User must be able to create custom agents, assign personality fragments, and view individual reasoning logs.
3. **Data Export**: System must allow exporting research runs into structured JSON/CSV for downstream analysis.
4. **Live Monitoring**: System must provide a real-time view of live market proxies framed against internal benchmarks.

#### 3.3.2 Non-Functional Requirements
1. **Performance**: Order matching in the kernel must complete in under 50ms to ensure a "smooth tape" experience.
2. **Reliability**: Any crash in the simulation must be recoverable via the Research Store's state persistence.
3. **Scalability**: The system should support up to 100 concurrent autonomous agents without a significant degradation in simulation speed.

### 3.4 Use Case Modeling
The primary actor is the **Quantitative Researcher**.
- **Use Case 1: Configure Run**: Selecting the scenario, dataset, and agent pool.
- **Use Case 2: Monitor Real-Time Tape**: Observing live order matching and agent decision-making.
- **Use Case 3: Performance Attribution**: Analyzing why specific agents outperformed others in a given macro-regime.

---

## 4. System Design

### 4.1 System Architecture
StockAI v2.0 utilizes a **Modular Micro-Kernel Architecture**.
1. **Communication Layer**: FastAPI handles routing and WebSocket synchronization.
2. **The Kernel**: The heart of the system. It manages the global simulation timer and order matching logic.
3. **The Agent Sandbox**: An isolated layer where LLM-driven agents observe the kernel state and emit orders.
4. **The Persistence Layer**: An E-R mapped SQLite database that stores all historical simulations.

### 4.2 Data Flow Diagrams (DFDs)
#### 4.2.1 Level 0: Global Context
The user sends "Config" and "Commands" to StockAI; StockAI returns "Market State", "Charts", and "Reports".

#### 4.2.2 Level 1: Functional Decomposition
- **Process 1.0 (Simulation Controller)**: Ingests user commands and drives the Kernel.
- **Process 2.0 (Agent Processor)**: Polls the Kernel for state and generates orders.
- **Process 3.0 (Analytics Engine)**: Processes Kernel logs into performance metrics.

### 4.3 E-R Diagram Description
- **RUN Entity**: The parent record. Contains duration, regime, and scenario.
- **AGENT Entity**: Belongs to a Run. Contains character type, risk profile, and PnL.
- **ORDER Entity**: Linked to an Agent and a Market State. Contains Symbol, Quantity, and Price.
- **EVENT Entity**: Captures macro-shocks (e.g., "News Injection") that affect all entities.

### 4.4 UML Design Descriptions
- **Sequence Diagram (Order Lifecycle)**: 
    1. Agent notices Price Move. 
    2. Agent queries LLM. 
    3. Agent sends Order to Kernel. 
    4. Kernel matches Order and emits "Fill" event.
- **Class Diagram**: Shows the inheritance hierarchy of `BaseAgent` -> `LLMAgent` and the composition of `MarketKernel` containing `OrderBook`.

*(Detailed expansion of these sections continues to fulfill the 80-90 page depth requirement...)*
