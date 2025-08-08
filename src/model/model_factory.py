"""
模型工厂类
负责根据配置创建不同类型的AI模型实例
"""

from typing import Dict, Any, Type
from .base_model import BaseModel
from .openai_model import OpenAIModel


class ModelFactory:
    """AI模型工厂类"""
    
    # 注册的模型类型
    _model_types: Dict[str, Type[BaseModel]] = {
        "openai": OpenAIModel,
        "openai_compatible": OpenAIModel,  # 别名
    }
    
    @classmethod
    def create_model(cls, model_type: str, config: Dict[str, Any]) -> BaseModel:
        """
        创建模型实例
        
        Args:
            model_type: 模型类型 ("openai", "openai_compatible" 等)
            config: 模型配置
            
        Returns:
            BaseModel: 模型实例
            
        Raises:
            ValueError: 不支持的模型类型
        """
        if model_type not in cls._model_types:
            supported_types = list(cls._model_types.keys())
            raise ValueError(f"Unsupported model type: {model_type}. "
                           f"Supported types: {supported_types}")
        
        model_class = cls._model_types[model_type]
        return model_class(config)
    
    @classmethod
    def register_model_type(cls, model_type: str, model_class: Type[BaseModel]):
        """
        注册新的模型类型
        
        Args:
            model_type: 模型类型名称
            model_class: 模型类
        """
        cls._model_types[model_type] = model_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """获取支持的模型类型列表"""
        return list(cls._model_types.keys())
    
    @classmethod
    def create_from_settings(cls, settings_instance) -> BaseModel:
        """
        从设置实例创建模型
        
        Args:
            settings_instance: 设置实例
            
        Returns:
            BaseModel: 模型实例
        """
        ai_config = settings_instance.get_ai_config()
        model_type = settings_instance.get_ai_model_type()
        
        return cls.create_model(model_type, ai_config)
