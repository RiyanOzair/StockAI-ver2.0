# 🤖 Modular Chatbot System

A production-ready, framework-agnostic conversational AI chatbot inspired by WhatsApp's Meta AI.

## 📁 Architecture

```
chatbot/
├── core/                  # Framework-agnostic core logic
│   ├── chat_engine.py     # Main orchestrator
│   ├── memory_manager.py  # Conversation context
│   ├── prompt_manager.py  # System prompts & templates
│   └── message_types.py   # Data structures
│
├── llm/                   # LLM abstraction layer
│   ├── llm_interface.py   # Abstract base class
│   └── mock_llm.py        # Mock implementation for testing
│
├── ui/                    # Streamlit UI components
│   └── floating_orb.py    # Floating chat widget
│
├── adapters/              # Platform adapters (future)
│   ├── web_adapter.py     # Web integration
│   └── whatsapp_adapter.py # WhatsApp (placeholder)
│
└── config/                # Configuration
    └── chatbot_config.py  # All settings
```

## ✨ Features

### Core Features
- **Framework-Agnostic**: Core logic works with any Python application
- **Provider-Agnostic**: Swap LLM providers easily (OpenAI, Groq, Gemini, etc.)
- **Memory Management**: Smart context retention with configurable limits
- **Clean Abstractions**: Well-defined interfaces for easy extension

### UI Features
- **Floating Orb**: Beautiful circular button (bottom-right)
- **Professional Design**: Glassmorphism, gradients, smooth animations
- **Responsive**: Works on desktop and mobile
- **Quick Actions**: Pre-defined question buttons
- **Typing Indicators**: Natural conversation feel

### Development Features
- **Mock LLM**: Test without API keys
- **Type Hints**: Full type annotations
- **Clean Code**: Well-documented, readable
- **Modular**: Easy to customize and extend

## 🚀 Quick Start

### Basic Usage

```python
from chatbot import ChatEngine, MockLLM, ChatbotConfig

# Create chatbot instance
llm = MockLLM()
engine = ChatEngine(llm=llm, memory_size=10)

# Process messages
response = await engine.process_message("Hello!")
print(response.text)  # Bot's response
print(response.confidence)  # "high", "medium", or "low"
```

### Streamlit Integration

```python
import streamlit as st
from chatbot.ui import render_floating_chatbot
from chatbot.config import ChatbotConfig

# Use default StockAI configuration
config = ChatbotConfig.for_stock_ai()

# Render floating chat orb
render_floating_chatbot(config=config)
```

### Custom Configuration

```python
from chatbot.config import ChatbotConfig

config = ChatbotConfig(
    bot_name="My Assistant",
    bot_avatar="🤖",
    memory_size=15,
    quick_actions=["Help me", "Explain this", "Show examples"],
    accent_color="#8b5cf6"
)
```

## 📝 Message Flow

1. **User Input** → Chat Engine
2. **Memory Manager** → Retrieves conversation context
3. **Prompt Manager** → Formats system prompt
4. **LLM Interface** → Generates response
5. **Memory Manager** → Stores messages
6. **Chat Response** → Returns to user

## 🔌 Adding a New LLM Provider

```python
from chatbot.llm import LLMInterface

class MyLLM(LLMInterface):
    async def generate_response(self, prompt: str, context: str) -> str:
        # Your LLM API call here
        return "Generated response"
    
    def is_available(self) -> bool:
        return True  # Check API key, etc.

# Use it
engine = ChatEngine(llm=MyLLM())
```

## ⚙️ Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `memory_size` | Number of messages to retain | 10 |
| `bot_name` | Display name of the bot | "StockAI Assistant" |
| `bot_avatar` | Emoji or icon | "🤖" |
| `welcome_message` | Initial greeting | "Hi! How can I help?" |
| `quick_actions` | Pre-defined questions | [...] |
| `accent_color` | UI theme color | "#8b5cf6" |

## 🎨 UI Customization

The floating orb UI is fully customizable through CSS variables and configuration:

```python
config = ChatbotConfig(
    accent_color="#26a69a",  # Change theme color
    orb_position=(30, 30),   # (right, bottom) pixels
    theme="dark"             # "dark" or "light"
)
```

## 🧪 Testing with MockLLM

The `MockLLM` provides deterministic responses for testing:

```python
from chatbot.llm import MockLLM

llm = MockLLM(
    simulate_delay=True,      # Simulate API latency
    delay_range=(0.3, 0.8)    # Delay in seconds
)

# Returns contextual mock responses
response = await llm.generate_response("Hello", "")
```

## 📦 Dependencies

- Python 3.8+
- Streamlit (for UI)
- asyncio (standard library)
- dataclasses (standard library)

## 🔮 Future Enhancements

- [ ] Real LLM providers (OpenAI, Groq, Gemini)
- [ ] Vector database for long-term memory
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] WhatsApp integration
- [ ] Slack integration
- [ ] Analytics and usage tracking

## 📚 Examples

See `examples/` directory for:
- Basic chatbot usage
- Custom LLM provider
- Streamlit integration
- Configuration examples

## 🤝 Contributing

Contributions welcome! The modular architecture makes it easy to add:
- New LLM providers
- New UI components
- New platform adapters
- Enhanced memory strategies

## 📄 License

Part of the StockAI project.
