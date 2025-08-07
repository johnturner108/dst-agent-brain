# DST Agent Brain

An intelligent AI agent system powered by Large Language Models (LLMs), designed for automation in Don't Starve Together game.

## 🎮 Project Overview

DST Agent Brain is an intelligent game agent system that integrates Large Language Model (LLM) to automatically execute various in-game tasks, including resource collection, tool crafting, survival strategies, and more. The system adopts a modular design with two main components: a game mod and an AI server.


## 🏗️ Project Structure

```
dst-agent-brain/
├── main.py                 # Main program entry point
├── requirements.txt        # Python dependencies
├── dst-agent-mod/         # Game mod
│   ├── modinfo.lua        # Mod information
│   ├── modmain.lua        # Mod main file
│   └── scripts/           # Mod scripts
├── src/                   # Source code
│   ├── api/              # API services
│   ├── config/           # Configuration management
│   ├── core/             # Core logic
│   ├── tools/            # Tool modules
│   └── utils/            # Utility functions
├── memory/               # Memory system
├── recipes/              # Recipe data
└── logs/                 # Log files
```

## 🚀 Quick Start

### Requirements
- Python 3.8+
- Don't Starve Together game

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd dst-agent-brain
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure AI service**
Edit the `src/config/settings.py` file to configure your AI API key:
```python
AI_API_KEY: str = "your-api-key-here"
AI_BASE_URL: str = "https://api.moonshot.cn/v1"
```

4. **Start the AI service**
```bash
python main.py
```

5. **Install the game mod**
- make a soft link in `D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods` to the `dst-agent-mod` folder to your game's mods directory
```shell
mklink /J "D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods\dst-agent-mod" "the dst-agent-mod file in this project"
```
- Enable the "DST Agent" mod in the game

## 📖 Usage Guide

### API Endpoints

#### Decision Interfaces
- `GET /{guid}/decide/Behaviour` - Get behavior decisions
- `GET /{guid}/decide/Dialog` - Get dialog decisions

#### Status Monitoring
- `GET /stats` - Get queue statistics
- `GET /inference-status` - Get inference status
- `GET /vision` - Get current perception information

#### Data Reception
- `POST /{guid}/perceptions` - Receive perception data
- `POST /{guid}/events` - Receive event data
- `POST /{guid}/command` - Receive commands from DST chat


## 🎯 Game Strategy

The system includes a comprehensive survival guide:

1. **Early Survival**: Collect basic resources (flint, grass, twigs)
2. **Tool Crafting**: Craft axes and pickaxes
3. **Resource Acquisition**: Cut trees, mine rocks, gather food
4. **Technology Development**: Find gold to craft science machines

## 🔧 Development Guide

### Core Components

- **Task**: Task management system
- **EventManager**: Event manager
- **ActionQueue**: Action queue
- **DialogQueue**: Dialog queue

### Extension Development

1. **Add New Tools**: Define new action formats in `src/tools/parse_tool.py`
2. **Modify AI Prompts**: Edit system prompts in `src/config/prompt.py`
3. **Custom Configuration**: Add new configuration items in `src/config/settings.py`

## 📝 Logging System

The system provides comprehensive logging:
- Application logs: `logs/app.log`
- Chat logs: `logs/chat_log/`
- Console output

## 🤝 Contributing

Issues and Pull Requests are welcome to improve the project!

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

Thanks to all developers and testers who have contributed to this project.

---

**Note**: Please ensure compliance with the game's terms of service and AI service provider's usage policies.
