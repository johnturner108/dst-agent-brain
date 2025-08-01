from openai import OpenAI
import openai
import threading
import time
from parse_tool import parse_assistant_message
import re
from prompt import systemPrompt
import json
import datetime

# 从 server.py 导入全局变量 current_action
# 这样 task.py 就可以访问并修改 server.py 中定义的 current_action 字典



class ToolExecutor:
    """
    ToolExecutor 类负责根据大型语言模型 (LLM) 返回的工具使用指令，
    更新应用程序的全局状态（即 current_action 字典）。
    """
    def __init__(self, action_queue, shared_perception_dict):

        self.action_queue = action_queue
        self.shared_perception_dict = shared_perception_dict
        print(f"ToolExecutor 初始化，动作队列: {self.action_queue} 和 感知字典：{self.shared_perception_dict}")
        

    def executeTool(self, content_blocks):
        def parse_action_str(action_str):
            # 解析动作字符串以提取动作类型 (Action) 和操作对象 (InvObject)
            # 示例：Action(BUILD, -, -, -, axe)
            action_match = re.match(r'Action\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+)\)\s*=\s*([^,]+)', action_str)
            if action_match:
                action_type = action_match.group(1) # 例如：BUILD
                inv_object = action_match.group(2) # 例如：axe
                posX = action_match.group(3)
                posZ = action_match.group(4)
                recipe = action_match.group(5)
                target = action_match.group(6)
            else:
                # 如果解析失败或模式不匹配，提供回退值并记录警告
                action_type = "UNKNOWN"
                inv_object = "-"
                print(f"警告: 无法解析动作字符串: {action_str}")
                return "警告: 无法解析动作字符串: {action_str}"

            # 清空并更新共享的 current_action 字典
            # 使用 clear() 和 update() 确保修改的是同一个字典对象，而不是创建新对象
            self.action_queue.put_action({
                "Type": "Action",
                "Action": action_type,
                "InvObject": inv_object,
                "Recipe": recipe,
                "Name": action_str, # 使用完整的动作字符串作为 Name
                "PosX": posX,
                "Target": target,
                "PosZ": posZ,
                "WFN": action_str # 使用完整的动作字符串作为 WFN
            })
        # print(f"正在执行工具，内容块: {content_blocks}")
        for block in content_blocks:
            # 检查当前块是否是类型为 'tool_use' 且名称为 'perform_action' 的工具指令
            if block.get('type') == 'tool_use' and block.get('name') == 'perform_action':
                params = block.get('params', {}) # 获取工具指令的参数
                if "\n" in params.get('action'):
                    action_strs = params.get('action').split("\n")
                    for action_str in action_strs:
                        parse_action_str(action_str)
                else:
                    action_str = params.get('action') # 例如：'Action(BUILD, -, -, -, axe)'
                    parse_action_str(action_str)
                # requires_approval = params.get('requires_approval') # 这个参数当前未在 current_action 中使用


                return # 执行第一个工具使用块后即返回，因为用户要求“中止”
            elif block.get('type') == 'tool_use' and block.get('name') == 'check_inventory':
                if block.get('params') == {}:
                    fields_to_keep = {"GUID", "Quantity", "Prefab"}
                    # item可能为空，需要处理
                    inventory = [
                        {key: item[key] for key in fields_to_keep if item and key in item}
                        for item in self.shared_perception_dict["ItemSlots"]
                    ]
                    return "Your current inventory has the following items:\n" + json.dumps(inventory, sort_keys=True)
                else:
                    item_name = block.get('params')['item_name']
                    quantity = 0
                    print(self.shared_perception_dict["ItemSlots"])
                    for item in self.shared_perception_dict["ItemSlots"]:
                        if item and item["Prefab"] == item_name:
                            quantity += item.get("Quantity", 0)
                    return "Your have {} {}.".format(quantity, item_name)
            elif block.get('type') == 'tool_use' and block.get('name') == 'check_equipslots':
                fields_to_keep = {"GUID", "Prefab"}
                inventory = [
                    {key: item[key] for key in fields_to_keep if key in item}
                    for item in self.shared_perception_dict["EquipSlots"]
                ]
                return "You are equipped with:\n" + json.dumps(inventory, sort_keys=True)
            elif block.get('type') == 'tool_use' and block.get('name') == 'check_surroundings':
                fields_to_keep = {"GUID", "Collectable", "Quantity", "Prefab", "X", "Z"}
                inventory = [
                    {key: item[key] for key in fields_to_keep if key in item}
                    for item in self.shared_perception_dict["Vision"]
                ]
                return "There are the following entities near you:\n" + json.dumps(inventory, sort_keys=True)
            elif block.get('type') == 'tool_use' and block.get('name') == 'task_completion':
                return
                    

        print("在内容块中未找到 'perform_action' 工具使用指令。")


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



    