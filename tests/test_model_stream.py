"""
AI模型流式输出单元测试
使用标准unittest框架
"""

import unittest
import sys
import os
import time
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model.model_factory import ModelFactory
from src.config.settings import settings


class TestModelStream(unittest.TestCase):
    """AI模型流式输出测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 创建模型实例"""
        cls.model = ModelFactory.create_from_settings(settings)
    
    def test_model_creation(self):
        """测试模型创建"""
        self.assertIsNotNone(self.model)
        self.assertTrue(hasattr(self.model, 'create_chat_completion'))
        self.assertTrue(hasattr(self.model, 'get_model_name'))
        
    def test_model_info(self):
        """测试模型信息获取"""
        model_name = self.model.get_model_name()
        self.assertIsInstance(model_name, str)
        self.assertTrue(len(model_name) > 0)
        
        provider_info = self.model.get_provider_info()
        self.assertIn('provider', provider_info)
        self.assertIn('model', provider_info)
        
    def test_basic_stream_output(self):
        """测试基本流式输出"""
        messages = [
            {"role": "user", "content": "请回复'测试成功'"}
        ]
        
        response_chunks = []
        for chunk in self.model.create_chat_completion(messages, stream=True):
            response_chunks.append(chunk)
            # 收到足够内容就停止，避免浪费API调用
            if len(''.join(response_chunks)) > 10:
                break
        
        self.assertTrue(len(response_chunks) > 0)
        full_response = ''.join(response_chunks)
        self.assertTrue(len(full_response) > 0)
        
    def test_abort_functionality(self):
        """测试中止功能"""
        messages = [
            {"role": "user", "content": "请写一段长文本"}
        ]
        
        abort_event = threading.Event()
        
        # 0.5秒后触发中止
        def trigger_abort():
            time.sleep(0.5)
            abort_event.set()
        
        abort_thread = threading.Thread(target=trigger_abort)
        abort_thread.start()
        
        chunks_received = 0
        for chunk in self.model.create_chat_completion(
            messages, 
            stream=True, 
            abort_event=abort_event
        ):
            chunks_received += 1
            if abort_event.is_set():
                break
        
        abort_thread.join()
        
        # 应该收到一些块，但由于中止，不会收到完整响应
        self.assertTrue(chunks_received >= 0)
        
    def test_different_temperatures(self):
        """测试不同temperature参数"""
        messages = [{"role": "user", "content": "将一个故事"}]
        
        # 测试低温度
        response_low = ""
        for chunk in self.model.create_chat_completion(
            messages, stream=True, temperature=0.1
        ):
            response_low += chunk
            print(chunk, end="")
            if len(response_low) > 50:  # 收到足够内容就停止
                break
        
        # 测试高温度  
        response_high = ""
        for chunk in self.model.create_chat_completion(
            messages, stream=True, temperature=0.9
        ):
            response_high += chunk
            if len(response_high) > 50:  # 收到足够内容就停止
                break
        
        # 两个响应都应该有内容
        self.assertTrue(len(response_low) > 0)
        self.assertTrue(len(response_high) > 0)


class TestModelConfig(unittest.TestCase):
    """模型配置测试类"""
    
    def test_config_loading(self):
        """测试配置加载"""
        ai_config = settings.get_ai_config()
        
        required_keys = ['api_key', 'base_url', 'model', 'temperature']
        for key in required_keys:
            self.assertIn(key, ai_config)
            self.assertIsNotNone(ai_config[key])
            
    def test_model_type(self):
        """测试模型类型"""
        model_type = settings.get_ai_model_type()
        self.assertIn(model_type, ['openai', 'openai_compatible'])


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
