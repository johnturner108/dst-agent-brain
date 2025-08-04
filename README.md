# DST Agent Brain

一个专为《饥荒：联机版》(Don't Starve Together) 设计的智能AI代理系统。

## 项目结构

```
dst-agent-brain/
├── main.py                 # 主入口文件
├── requirements.txt        # 项目依赖
├── README.md              # 项目说明
├── .gitignore             # Git忽略文件
├── src/                   # 源代码目录
│   ├── __init__.py        # 包初始化文件
│   ├── core/              # 核心业务逻辑
│   │   ├── __init__.py
│   │   └── task.py        # 任务处理核心类
│   ├── api/               # API相关代码
│   │   ├── __init__.py
│   │   └── server.py      # FastAPI服务器
│   ├── tools/             # 工具执行器
│   │   ├── __init__.py
│   │   ├── parse_tool.py  # 工具解析器
│   │   └── tool_executor.py # 工具执行器
│   ├── utils/             # 工具类和辅助函数
│   │   ├── __init__.py
│   │   └── queues.py      # 队列管理类
│   ├── config/            # 配置文件
│   │   ├── __init__.py
│   │   └── prompt.py      # AI提示词配置
│   ├── data/              # 数据文件
│   │   ├── recipes/       # 菜谱数据
│   │   ├── memory/        # 记忆数据
│   │   └── guide.md       # 游戏指南
│   └── logs/              # 日志文件
└── chat_log/              # 聊天日志（旧目录，保留兼容性）
```

## 功能特性

- 🤖 **智能AI代理**: 基于大型语言模型的游戏AI
- 🎮 **游戏自动化**: 自动执行各种游戏动作
- 🗺️ **地图记忆**: 智能标记和记忆重要位置
- 🔍 **环境观察**: 实时监控周围环境变化
- 📊 **状态管理**: 完整的角色状态和库存管理
- 🌐 **RESTful API**: 提供完整的HTTP API接口

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务器

```bash
python main.py
```

服务器将在 `http://localhost:8081` 启动。

### API端点

- `GET /{guid}/decide/Behaviour` - 获取行为决策
- `GET /{guid}/decide/Dialog` - 获取对话内容
- `POST /{guid}/perceptions` - 接收感知数据
- `POST /{guid}/events` - 接收游戏事件
- `POST /{guid}/command` - 执行用户命令
- `GET /stats` - 获取系统统计信息
- `GET /inference-status` - 获取推理状态
- `GET /abort-inference` - 中止当前推理

## 配置说明

### API密钥配置

在 `src/core/task.py` 中配置你的AI API密钥：

```python
self.client = OpenAI(
    api_key="your-api-key-here",
    base_url="https://api.moonshot.cn/v1",
)
```

### 模型配置

支持多种AI模型：
- `kimi-k2-0711-preview` (默认)
- `qwen-plus`

## 开发指南

### 代码结构说明

1. **core模块**: 包含核心业务逻辑，主要是Task类，负责AI对话和任务处理
2. **api模块**: FastAPI服务器和所有HTTP端点
3. **tools模块**: 工具执行器，负责解析和执行AI的工具调用
4. **utils模块**: 工具类，包括队列管理和辅助函数
5. **config模块**: 配置文件和AI提示词模板
6. **data模块**: 数据文件，包括菜谱、记忆和指南
7. **logs模块**: 应用程序日志

### 添加新功能

1. 在相应模块中添加新功能
2. 更新API端点（如需要）
3. 添加相应的测试
4. 更新文档

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v1.0.0
- 重构项目结构，提高代码组织性
- 分离核心模块和API模块
- 改进日志系统
- 添加完整的文档 