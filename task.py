from openai import OpenAI
import openai
import threading
import time
from parse_tool import parse_assistant_message
import re
from prompt import systemPrompt
import json
import datetime
from tool_executor import ToolExecutor

# 从 server.py 导入全局变量 current_action
# 这样 task.py 就可以访问并修改 server.py 中定义的 current_action 字典






class Task:
    def __init__(self, action_queue, current_perception):
        self.client = OpenAI(
            api_key = "sk-L7Q2cBME4D7Oip201OQicXPrrcbNXP2Rufq4sVtYZtFQlbEb", # 在这里将 MOONSHOT_API_KEY 替换为你从 Kimi 开放平台申请的 API Key
            base_url = "https://api.moonshot.cn/v1",
        )
        self.toolExecutor = ToolExecutor(action_queue, current_perception)
        self.messages = [
            {"role": "system", "content": systemPrompt()},
        ]
        # 根据时间戳命名日志文件
        self.log_file = "chat_log_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
        
        # 添加线程管理
        self.current_thread = None
        self.abort_event = threading.Event()
        self.thread_lock = threading.Lock()

    def createMessage(self, abort_event):
        
        try:
            stream = self.client.chat.completions.create(
                model="kimi-k2-0711-preview",
                messages=self.messages,
                temperature=0.6,
                stream=True,
            )
            full_message = ""
            for chunk in stream:
                # Check if the abort event has been set by another thread.
                if abort_event.is_set():
                    print("\n[Stream aborted by user]")
                    break  # Exit the loop if abortion is requested.

                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
                    full_message += delta.content
                    content_blocks, has_tool_use = parse_assistant_message(full_message)
                    # print(content_blocks)
                    # print(has_tool_use)
                    if has_tool_use:
                        print("has tool use")
                        return
                    # print(delta.content, end="")
                    
        except openai.APIError as e:
            # Handle potential API errors (e.g., connection issues, invalid key)
            print(f"An API error occurred: {e}")
            yield "Sorry, there was an error with the service."
        except Exception as e:
            # Handle other unexpected errors
            print(f"An unexpected error occurred: {e}")
            yield "An unexpected error occurred."

    def processStream(self, user_message):
        # 使用锁确保同时只有一个推理线程在运行
        with self.thread_lock:
            # 如果有正在运行的线程，先终止它
            if self.current_thread and self.current_thread.is_alive():
                print("[Task] Aborting previous inference...")
                self.abort_event.set()
                self.current_thread.join(timeout=2.0)  # 等待最多2秒
            
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

# --- Example Usage ---

# if __name__ == "__main__":
#     # 1. Create a threading.Event object to control the stream.
#     abort_signal = threading.Event()

#     # 2. Define the initial conversation messages.
#     initial_messages = [
#         {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手..."},
#         {"role": "user", "content": "请给我讲一个关于太空探索的简短故事。"}
#     ]

#     print("--- Starting stream (will abort in 1.5 seconds) ---")

#     # 3. Create a thread that will set the abort signal after a delay.
#     # This simulates a user sending a new command or closing the window.
#     # def interrupt_stream():
#     #     time.sleep(1.5)
#     #     print("\n[Sending abort signal...]")
#     #     abort_signal.set()

#     # interrupt_thread = threading.Thread(target=interrupt_stream)
#     # interrupt_thread.start()

#     # 4. Call the generator function and print the yielded content.
#     full_response = ""
#     try:
#         stream = createMessage(initial_messages, abort_signal)
#         for content_chunk in stream:
#             print(content_chunk, end="", flush=True)
#             full_response += content_chunk
#     except KeyboardInterrupt:
#         print("\n[Stream interrupted by keyboard]")

#     # It's good practice to wait for the thread to finish.
#     # interrupt_thread.join()

#     print("\n\n--- Full response received before abort ---")
#     print(full_response)
#     print("\n--- Example finished ---")

#     # --- Example of a full, uninterrupted stream ---
#     print("\n\n--- Starting a new, uninterrupted stream ---")
#     uninterrupted_messages = [
#         {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手..."},
#         {"role": "user", "content": "请给我讲一个关于太空探索的简短故事。"}
#     ]
#     # We need a new event object that is not set.
#     new_abort_signal = threading.Event()
#     full_story = ""
#     for content_chunk in createMessage(uninterrupted_messages, new_abort_signal):
#         print(content_chunk, end="", flush=True)
#         full_story += content_chunk
    
#     print("\n\n--- Full story ---")
#     print(full_story)


if __name__ == "__main__":
    

    vision = '''
  "Vision": [
    {
      "GUID": 107210,
      "Fuel": false,
      "Collectable": true,
      "Fueled": false,
      "Prefab": "grass",
      "Equippable": false,
      "Choppable": false,
      "X": -481.67001342773,
      "Mineable": false,
      "Y": 0,
      "Hammerable": false,
      "Quantity": 1,
      "Cooker": false,
      "Z": 21.89999961853,
      "Cookable": false,
      "Stewer": false,
      "Diggable": true,
      "Grower": false
    },'''
    # --- Example of a full, uninterrupted stream ---
    print("\n\n--- Starting a new, uninterrupted stream ---")
    current_action = {}
    task = Task(current_action)
    
    task.processStream("捡一个草" + vision)
    # We need a new event object that is not set.



    