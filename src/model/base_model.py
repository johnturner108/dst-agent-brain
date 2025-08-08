"""
基础AI模型抽象类
定义所有AI模型的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, List


class BaseModel(ABC):
    """AI模型基类，定义统一接口"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化模型
        
        Args:
            config: 模型配置字典
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """验证配置参数，子类需要实现"""
        pass
    
    @abstractmethod
    def create_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True,
        **kwargs
    ) -> Iterator[str]:
        """
        创建聊天完成
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Yields:
            str: 流式输出的内容块
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.config.copy()
