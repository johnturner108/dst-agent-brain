# DST Agent Brain - 项目结构改进建议

## 当前问题分析

1. **代码耦合度高**：`server.py` 包含了太多职责，既是HTTP服务器又是业务逻辑处理器
2. **全局状态管理混乱**：多个模块共享全局变量，难以测试和维护
3. **配置硬编码**：API密钥等配置直接写在代码中
4. **缺乏模块化**：工具执行器、队列管理等功能没有清晰的边界
5. **错误处理不统一**：不同模块的错误处理方式不一致

## 建议的新项目结构

```
dst-agent-brain/
├── README.md
├── requirements.txt
├── config/
│   ├── __init__.py
│   ├── settings.py          # 配置管理
│   └── logging_config.py    # 日志配置
├── src/
│   ├── __init__.py
│   ├── main.py              # 应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py     # 代理相关路由
│   │   │   ├── events.py    # 事件处理路由
│   │   │   └── status.py    # 状态查询路由
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py      # 认证中间件
│   │   │   └── logging.py   # 日志中间件
│   │   └── dependencies.py  # 依赖注入
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py         # 代理核心逻辑
│   │   ├── state.py         # 状态管理
│   │   └── exceptions.py    # 自定义异常
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py   # LLM服务
│   │   ├── tool_service.py  # 工具执行服务
│   │   ├── queue_service.py # 队列管理服务
│   │   └── memory_service.py # 记忆管理服务
│   ├── models/
│   │   ├── __init__.py
│   │   ├── action.py        # 动作模型
│   │   ├── perception.py    # 感知数据模型
│   │   ├── event.py         # 事件模型
│   │   └── response.py      # 响应模型
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── parsers.py       # 解析工具
│   │   ├── validators.py    # 验证工具
│   │   └── helpers.py       # 辅助函数
│   └── data/
│       ├── __init__.py
│       ├── recipes/
│       │   ├── __init__.py
│       │   ├── processor.py # 菜谱处理器
│       │   └── models.py    # 菜谱模型
│       └── memory/
│           ├── __init__.py
│           ├── map_manager.py # 地图管理器
│           └── persistence.py # 数据持久化
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── development.md
└── scripts/
    ├── setup.py
    └── deploy.py
```

## 核心改进点

### 1. 依赖注入和状态管理

```python
# src/core/state.py
from dataclasses import dataclass
from typing import Dict, Any
from src.services.queue_service import ActionQueue, DialogQueue

@dataclass
class AgentState:
    """代理状态管理"""
    current_perception: Dict[str, Any]
    self_uid: str
    action_queue: ActionQueue
    dialog_queue: DialogQueue
    
    def update_perception(self, perception: Dict[str, Any]):
        self.current_perception.clear()
        self.current_perception.update(perception)
```

### 2. 服务层抽象

```python
# src/services/llm_service.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any

class LLMService(ABC):
    @abstractmethod
    async def generate_response(self, messages: list, stream: bool = True) -> AsyncGenerator[str, None]:
        pass

class MoonshotLLMService(LLMService):
    def __init__(self, api_key: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    async def generate_response(self, messages: list, stream: bool = True):
        # 实现流式响应生成
        pass
```

### 3. 路由模块化

```python
# src/api/routes/agent.py
from fastapi import APIRouter, Depends
from src.core.state import AgentState
from src.services.agent_service import AgentService

router = APIRouter(prefix="/{guid}")

@router.get("/decide/{layer}")
async def decide(
    guid: str, 
    layer: str, 
    agent_service: AgentService = Depends()
):
    return await agent_service.decide(guid, layer)
```

### 4. 配置管理

```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    api_key: str
    base_url: str = "https://api.moonshot.cn/v1"
    model_name: str = "kimi-k2-0711-preview"
    max_queue_size: int = 20
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
```

### 5. 错误处理统一化

```python
# src/core/exceptions.py
class AgentException(Exception):
    """代理基础异常"""
    pass

class ToolExecutionError(AgentException):
    """工具执行错误"""
    pass

class LLMServiceError(AgentException):
    """LLM服务错误"""
    pass
```

## 迁移步骤

1. **创建新的目录结构**
2. **逐步迁移现有代码**：
   - 首先迁移工具类（utils.py, parse_tool.py）
   - 然后迁移服务层（task.py, tool_executor.py）
   - 最后重构API层（server.py）
3. **添加配置管理**
4. **实现依赖注入**
5. **添加测试覆盖**
6. **更新文档**

## 优势

1. **可维护性**：清晰的模块边界和职责分离
2. **可测试性**：依赖注入使得单元测试更容易
3. **可扩展性**：服务层抽象使得添加新功能更容易
4. **配置管理**：环境变量和配置文件分离
5. **错误处理**：统一的异常处理机制
6. **文档化**：清晰的API文档和开发指南 