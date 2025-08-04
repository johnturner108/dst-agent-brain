# 代码重构示例

## 1. 配置管理重构

### 当前代码 (task.py)
```python
self.client = OpenAI(
    api_key = "sk-L7Q2cBME4D7Oip201OQicXPrrcbNXP2Rufq4sVtYZtFQlbEb",
    base_url = "https://api.moonshot.cn/v1",
)
```

### 重构后 (config/settings.py)
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM配置
    moonshot_api_key: str
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    moonshot_model: str = "kimi-k2-0711-preview"
    
    # 队列配置
    max_action_queue_size: int = 20
    max_dialog_queue_size: int = 20
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(levelname)s - %(message)s"
    
    # 文件路径配置
    memory_dir: str = "./memory"
    chat_log_dir: str = "./chat_log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局设置实例
settings = Settings()
```

### 重构后 (src/services/llm_service.py)
```python
from openai import OpenAI
from config.settings import settings
from src.core.exceptions import LLMServiceError
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
        )
        self.model = settings.moonshot_model
    
    async def generate_stream_response(self, messages: list):
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.6,
                stream=True,
            )
            
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
                    
        except Exception as e:
            logger.error(f"LLM服务错误: {e}")
            raise LLMServiceError(f"生成响应失败: {e}")
```

## 2. 状态管理重构

### 当前代码 (server.py)
```python
# 全局状态对象
action_queue = ActionQueue(maxsize=20)
dialog_queue = DialogQueue(maxsize=20)
current_perception: Dict = {}
self_uid = 0
task_instance = Task(action_queue, current_perception, dialog_queue, self_uid)
```

### 重构后 (src/core/state.py)
```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.services.queue_service import ActionQueue, DialogQueue
from config.settings import settings
import threading

@dataclass
class AgentState:
    """代理状态管理"""
    guid: str
    current_perception: Dict[str, Any] = field(default_factory=dict)
    action_queue: ActionQueue = field(default_factory=lambda: ActionQueue(settings.max_action_queue_size))
    dialog_queue: DialogQueue = field(default_factory=lambda: DialogQueue(settings.max_dialog_queue_size))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def update_perception(self, perception: Dict[str, Any]):
        """线程安全地更新感知数据"""
        with self._lock:
            self.current_perception.clear()
            self.current_perception.update(perception)
    
    def get_perception(self) -> Dict[str, Any]:
        """线程安全地获取感知数据"""
        with self._lock:
            return self.current_perception.copy()

class StateManager:
    """状态管理器，管理多个代理的状态"""
    def __init__(self):
        self._states: Dict[str, AgentState] = {}
        self._lock = threading.Lock()
    
    def get_or_create_state(self, guid: str) -> AgentState:
        """获取或创建代理状态"""
        with self._lock:
            if guid not in self._states:
                self._states[guid] = AgentState(guid=guid)
            return self._states[guid]
    
    def remove_state(self, guid: str):
        """移除代理状态"""
        with self._lock:
            self._states.pop(guid, None)

# 全局状态管理器
state_manager = StateManager()
```

## 3. 路由重构

### 当前代码 (server.py)
```python
@app.get("/{guid}/decide/{layer}")
async def decide(guid: str, layer: str):
    global self_uid
    self_uid = guid
    if layer == "Behaviour":
        response_data = action_queue.get_action()
        return JSONResponse(content=response_data)
    elif layer == "Dialog":
        response_data = {"Type": "Speak", "Utterance": dialog_queue.get_dialog()}
        return JSONResponse(content=response_data)
    else:
        raise HTTPException(status_code=404, detail="Layer not found")
```

### 重构后 (src/api/routes/agent.py)
```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.core.state import state_manager
from src.services.agent_service import AgentService
from src.models.response import DecisionResponse
from src.core.exceptions import InvalidLayerError

router = APIRouter(prefix="/{guid}")

def get_agent_service(guid: str) -> AgentService:
    """依赖注入：获取代理服务"""
    state = state_manager.get_or_create_state(guid)
    return AgentService(state)

@router.get("/decide/{layer}", response_model=DecisionResponse)
async def decide(
    guid: str, 
    layer: str, 
    agent_service: AgentService = Depends(get_agent_service)
):
    try:
        response_data = await agent_service.decide(layer)
        return JSONResponse(content=response_data)
    except InvalidLayerError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"决策失败: {e}")
```

### 重构后 (src/services/agent_service.py)
```python
from typing import Dict, Any
from src.core.state import AgentState
from src.core.exceptions import InvalidLayerError
import logging

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, state: AgentState):
        self.state = state
    
    async def decide(self, layer: str) -> Dict[str, Any]:
        """代理决策逻辑"""
        if layer == "Behaviour":
            return self.state.action_queue.get_action()
        elif layer == "Dialog":
            return {
                "Type": "Speak", 
                "Utterance": self.state.dialog_queue.get_dialog()
            }
        else:
            raise InvalidLayerError(f"不支持的分层: {layer}")
    
    async def update_perception(self, perception: Dict[str, Any]):
        """更新感知数据"""
        self.state.update_perception(perception)
        logger.info(f"代理 {self.state.guid} 感知数据已更新")
    
    async def process_event(self, event: Dict[str, Any]):
        """处理游戏事件"""
        # 事件处理逻辑
        pass
```

## 4. 工具执行器重构

### 当前代码 (tool_executor.py)
```python
class ToolExecutor:
    def __init__(self, task_instance, action_queue, shared_perception_dict, dialog_queue, self_uid):
        self.task_instance = task_instance
        self.action_queue = action_queue
        self.dialog_queue = dialog_queue
        self.shared_perception_dict = shared_perception_dict
        # ... 其他初始化
```

### 重构后 (src/services/tool_service.py)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.core.state import AgentState
from src.core.exceptions import ToolExecutionError
from src.models.action import Action
from src.data.memory.map_manager import MapManager
import logging

logger = logging.getLogger(__name__)

class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, state: AgentState):
        self.state = state
        self.map_manager = MapManager()
        self._tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, callable]:
        """注册所有可用工具"""
        return {
            'perform_action': self._execute_perform_action,
            'check_inventory': self._execute_check_inventory,
            'check_surroundings': self._execute_check_surroundings,
            'mark_loc': self._execute_mark_loc,
            'check_map': self._execute_check_map,
            'observer': self._execute_observer,
        }
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """执行指定工具"""
        if tool_name not in self._tools:
            raise ToolExecutionError(f"未知工具: {tool_name}")
        
        try:
            return await self._tools[tool_name](params)
        except Exception as e:
            logger.error(f"工具执行失败 {tool_name}: {e}")
            raise ToolExecutionError(f"工具 {tool_name} 执行失败: {e}")
    
    async def _execute_perform_action(self, params: Dict[str, Any]) -> str:
        """执行动作"""
        action_str = params.get('action')
        if not action_str:
            raise ToolExecutionError("缺少动作参数")
        
        action = Action.from_string(action_str)
        self.state.action_queue.put_action(action.to_dict())
        
        return f"动作已添加到队列: {action.action_type}"
    
    async def _execute_check_inventory(self, params: Dict[str, Any]) -> str:
        """检查背包"""
        perception = self.state.get_perception()
        inventory = perception.get("ItemSlots", [])
        equips = perception.get("EquipSlots", [])
        
        return f"背包: {inventory}\n装备: {equips}"
```

## 5. 模型定义

### 重构后 (src/models/action.py)
```python
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class Action:
    """动作模型"""
    action_type: str
    inv_object: str = "-"
    pos_x: str = "-"
    pos_z: str = "-"
    recipe: str = "-"
    target: str = "-"
    
    @classmethod
    def from_string(cls, action_str: str) -> 'Action':
        """从字符串解析动作"""
        pattern = r'Action\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)\)\s*=\s*([^,]+)'
        match = re.match(pattern, action_str)
        
        if not match:
            raise ValueError(f"无效的动作格式: {action_str}")
        
        return cls(
            action_type=match.group(1),
            inv_object=match.group(2),
            pos_x=match.group(3),
            pos_z=match.group(4),
            recipe=match.group(5),
            target=match.group(6)
        )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "Type": "Action",
            "Action": self.action_type,
            "InvObject": self.inv_object,
            "Recipe": self.recipe,
            "Name": str(self),
            "PosX": self.pos_x,
            "Target": self.target,
            "PosZ": self.pos_z,
            "WFN": str(self),
            "AUID": str(hash(self))[:4]
        }
    
    def __str__(self) -> str:
        return f"Action({self.action_type}, {self.inv_object}, {self.pos_x}, {self.pos_z}, {self.recipe}) = {self.target}"
```

## 6. 主应用入口

### 重构后 (src/main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes import agent, events, status
from src.core.exceptions import AgentException
from fastapi.responses import JSONResponse
import logging

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)

# 创建FastAPI应用
app = FastAPI(
    title="DST Agent Brain",
    description="饥荒游戏AI代理系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agent.router, tags=["agent"])
app.include_router(events.router, tags=["events"])
app.include_router(status.router, tags=["status"])

# 全局异常处理
@app.exception_handler(AgentException)
async def agent_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8081,
        reload=True
    )
```

## 7. 环境变量配置

### 重构后 (.env)
```env
# LLM配置
MOONSHOT_API_KEY=sk-L7Q2cBME4D7Oip201OQicXPrrcbNXP2Rufq4sVtYZtFQlbEb
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=kimi-k2-0711-preview

# 队列配置
MAX_ACTION_QUEUE_SIZE=20
MAX_DIALOG_QUEUE_SIZE=20

# 日志配置
LOG_LEVEL=INFO

# 文件路径
MEMORY_DIR=./memory
CHAT_LOG_DIR=./chat_log
```

这样的重构将带来以下好处：

1. **更好的可维护性**：每个模块职责清晰，易于理解和修改
2. **更强的可测试性**：依赖注入使得单元测试更容易编写
3. **更高的可扩展性**：新功能可以通过添加新的服务或路由来实现
4. **更安全的配置管理**：敏感信息通过环境变量管理
5. **更统一的错误处理**：所有异常都有统一的处理机制
6. **更好的文档化**：清晰的API文档和代码注释 