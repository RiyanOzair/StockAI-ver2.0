## 1. High-Level Architecture (V2)
The following descriptive diagram illustrates the architectural layers of StockAI 2.0.

![System Architecture V2](./architecture_v2.png)

---

## 2. UML Diagram Suite
A comprehensive visual suite of the project's core logic and data flow.

![UML Suite](./uml_suite.png)

---

## 3. Mermaid Source Diagrams
The following sections provide the live Mermaid code for maintenance and expansion.

### 2.1 Class Diagram (Core Data Models)
This diagram shows the relationships between orders, trades, agents, and simulation snapshots.

```mermaid
classDiagram
    class Order {
        +String id
        +String agent_id
        +String symbol
        +OrderSide side
        +OrderType type
        +float price
        +int quantity
        +OrderStatus status
        +datetime timestamp
    }
    class Trade {
        +String trade_id
        +String buy_order_id
        +String sell_order_id
        +float price
        +int quantity
        +datetime timestamp
    }
    class BaseAgent {
        +String id
        +String name
        +AgentPersona persona
        +Wallet wallet
        +List loans
        +get_snapshot(prices)
        +act(market_state)
    }
    class DaySnapshot {
        +int day
        +Dict prices
        +List agent_summaries
        +int total_trades
    }
    class SimulationLoop {
        +int day
        +int session
        +List snapshots
        +List all_trades
        +step(market_state)
        +run_simulation()
    }

    SimulationLoop "1" *-- "many" Order : matching_engine
    SimulationLoop "1" *-- "many" Trade : history
    SimulationLoop "1" *-- "many" BaseAgent : agents
    SimulationLoop "1" *-- "many" DaySnapshot : persistent_rewind
    BaseAgent "1" -- "many" Order : submits
    BaseAgent "1" -- "many" Trade : fills
```

### 2.2 Sequence Diagram (Simulation Step Lifecycle)
This diagram illustrates the flow of data during a single simulation step.

```mermaid
sequenceDiagram
    participant SL as SimulationLoop
    participant MK as MarketKernel
    participant AP as AnalyticsProvider
    participant AG as AI Agents
    participant DB as SQLite Store

    loop Every Session Phase
        SL->>MK: Update Price (Correlated Walk)
        MK->>AP: Compute Market Analytics
        AP-->>SL: Breadth, Sentiment, Volatility
        SL->>AG: Request Actions (MarketState + News)
        AG-->>SL: Emits Orders (BUY/SELL)
        SL->>MK: Match Orders (Priority Queue)
        MK-->>SL: Fill Events (Trades)
        SL->>DB: Record Run Events
        alt End of Day
            SL->>SL: Take DaySnapshot
            SL->>DB: Persistent Save
        end
    end
```

### 2.3 Data Flow Diagram (Market Intelligence)
How live market data reaches the Performance Monitor.

```mermaid
graph TD
    A[Yahoo Finance v8 API] -->|HTTPS| B(live_market_service.py)
    B -->|Fetch/JSON| C{120s Cache?}
    C -->|Yes| D[Return Cached Snapshot]
    C -->|No| E[Execute New Provider Fetch]
    E -->|Success| F[Refresh Cache & Return]
    E -->|Failure| G[Build Stale or Fallback Response]
    D --> H[live-market.html Frontend]
    F --> H
    G --> H
    H -->|Render| I[User Interface]
```

### 2.4 Entity-Relationship (E-R) Diagram
The layout of the persistent research store.

```mermaid
erDiagram
    RUN ||--o{ RUN_EVENT : logs
    RUN ||--o{ EVALUATION : output
    DATASET ||--o| RUN : configures
    SCENARIO ||--o| RUN : configures
    STRATEGY_BOT ||--o{ EVALUATION : benchmarks
    EXPERIMENT ||--o{ RUN : contains

    RUN {
        string run_id
        string status
        json config_snapshot
    }
    RUN_EVENT {
        int sequence
        string event_type
        json payload
    }
```
