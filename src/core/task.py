import threading
import time
import re
import json
import datetime
import os
from ..tools.parse_tool import parse_assistant_message
from ..config.prompt import systemPrompt
from ..tools.tool_executor import ToolExecutor
from ..config.settings import settings
from ..model.model_factory import ModelFactory

class Task:
    def __init__(self, action_queue, current_perception, dialog_queue, self_uid):
        # 使用模型工厂创建AI模型实例
        self.model = ModelFactory.create_from_settings(settings)
        self.toolExecutor = ToolExecutor(self, action_queue, current_perception, dialog_queue, self_uid)
        self.dialog_queue = dialog_queue
        self.messages = [
            {"role": "system", "content": systemPrompt()},
        ]
        
        # 确保日志目录存在
        if not os.path.exists(settings.CHAT_LOG_DIR):
            os.makedirs(settings.CHAT_LOG_DIR)
        # 根据时间戳命名日志文件
        self.log_file = os.path.join(settings.CHAT_LOG_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")
        
        # 添加线程管理
        self.current_thread = None
        self.abort_event = threading.Event()
        self.thread_lock = threading.Lock()

    def createMessage(self, abort_event):
        """
        使用模型创建消息流
        
        Args:
            abort_event: 中止事件
            
        Yields:
            str: 流式输出的内容块
        """
        full_message = ""
        
        for content_chunk in self.model.create_chat_completion(
            messages=self.messages,
            stream=True,
            abort_event=abort_event
        ):
            yield content_chunk
            full_message += content_chunk
            content_blocks, has_tool_use = parse_assistant_message(full_message)
            
            if has_tool_use:
                print("has tool use")
                return

    def processStream(self, user_message):
        # 使用锁确保同时只有一个推理线程在运行
        with self.thread_lock:
            # 如果有正在运行的线程，先终止它
            if self.current_thread and self.current_thread.is_alive():
                print("[Task] Aborting previous inference...")
                self.abort_event.set()
                self.current_thread.join(timeout=2.0)  # 等待最多2秒
                # self.current_thread.join()
            
            # 重置abort事件
            self.abort_event.clear()
            
            # 创建新的推理线程
            self.current_thread = threading.Thread(
                target=self._processStreamInternal,
                args=(user_message,),
                daemon=True
            )
            self.current_thread.start()
    
    def _processStreamInternal(self, user_message):
        """内部方法，实际执行推理逻辑"""
        try:
            print(f"[Task] Starting new inference: {user_message[:50]}...")
            self.messages.append({"role": "user", "content": user_message})
            self.writeLog({"role": "user", "content": user_message})
            
            full_message = ""
            for content_chunk in self.createMessage(self.abort_event):
                if self.abort_event.is_set():
                    print("[Task] Inference aborted")
                    return
                print(content_chunk, end="", flush=True)
                full_message += content_chunk
            
            if not self.abort_event.is_set():
                print("[Message] Assistant: " + full_message)
                self.messages.append({"role": "assistant", "content": full_message})
                self.writeLog({"role": "assistant", "content": full_message})
                content_blocks, has_tool_use = parse_assistant_message(full_message)
                self.add_to_dialog_queue(content_blocks)
                result = self.toolExecutor.executeTool(content_blocks)
                if result and not self.abort_event.is_set():
                    self._processStreamInternal(result)
        except Exception as e:
            print(f"[Task] Error in inference: {e}")
        
    def writeLog(self, message):
        timestamp = datetime.datetime.now().isoformat()
        with open(self.log_file, "a", encoding="utf-8") as log:
            log.write(f"\n\n[Time] {timestamp} ")
            log.write(message["role"] + "\n" + message["content"])
    
    def is_inference_running(self):
        """检查当前是否有推理正在进行"""
        with self.thread_lock:
            return self.current_thread is not None and self.current_thread.is_alive()
    
    def abort_current_inference(self):
        """强制终止当前推理"""
        with self.thread_lock:
            if self.current_thread and self.current_thread.is_alive():
                print("[Task] Force aborting current inference...")
                self.abort_event.set()
                self.current_thread.join(timeout=1.0)
                return True
            return False
        
    def add_to_dialog_queue(self, content_blocks):
        for block in content_blocks:
            if block.get('type') == 'text':
                self.dialog_queue.put_dialog(block["content"])
            if block.get('type') == 'tool_use' and block.get('name') == "task_completion":
                self.dialog_queue.put_dialog("Task Complete:" + block["params"].get("result", "")) 