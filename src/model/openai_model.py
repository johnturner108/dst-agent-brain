"""
OpenAI兼容模型实现
支持OpenAI API规格的所有服务提供商
"""

from typing import Dict, Any, Iterator, List
import openai
from openai import OpenAI

from .base_model import BaseModel


class OpenAIModel(BaseModel):
    """OpenAI兼容模型实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url"),
        )
    
    def _validate_config(self) -> None:
        """验证OpenAI配置参数"""
        required_keys = ["api_key", "model"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
    
    def create_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True,
        abort_event=None,
        **kwargs
    ) -> Iterator[str]:
        """
        创建OpenAI聊天完成
        
        Args:
            messages: 消息列表
            stream: 是否流式输出
            abort_event: 中止事件
            **kwargs: 其他参数
            
        Yields:
            str: 流式输出的内容块
        """
        try:
            # 合并配置参数
            params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": self.config.get("temperature", 0.6),
                "stream": stream,
                **kwargs
            }
            
            if stream:
                stream_response = self.client.chat.completions.create(**params)
                
                for chunk in stream_response:
                    # 检查中止事件
                    if abort_event and abort_event.is_set():
                        print("\n[Stream aborted by user]")
                        break
                    
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                
        except openai.APIError as e:
            print(f"An API error occurred: {e}")
            yield "Sorry, there was an error with the service."
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            yield "An unexpected error occurred."


    def create_chat_completion_once(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        创建OpenAI聊天完成
        """
        params = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": self.config.get("temperature", 0.6),
            "stream": False,
            **kwargs
        }
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.config["model"]
    
    def get_provider_info(self) -> Dict[str, str]:
        """获取提供商信息"""
        base_url = self.config.get("base_url", "https://api.openai.com/v1")
        
        # 根据base_url判断提供商
        if "moonshot.cn" in base_url:
            provider = "Moonshot"
        elif "dashscope.aliyuncs.com" in base_url:
            provider = "Alibaba Cloud"
        elif "api.openai.com" in base_url:
            provider = "OpenAI"
        else:
            provider = "Custom"
            
        return {
            "provider": provider,
            "base_url": base_url,
            "model": self.get_model_name()
        }
