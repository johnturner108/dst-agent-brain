import threading
import time
import re
import json
import datetime
import os
from ..tools.parse_tool import parse_assistant_message
from ..config.prompt import system_prompt_summarize, systemPrompt, instruction_summarize
from ..tools.tool_executor import ToolExecutor
from ..config.settings import settings
from ..model.model_factory import ModelFactory

class Task:
    def __init__(self, action_queue, current_perception, dialog_queue, self_uid):
        # 使用模型工厂创建AI模型实例
        self.model = ModelFactory.create_from_settings(settings)
        self.toolExecutor = ToolExecutor(self, action_queue, current_perception, dialog_queue, self_uid)
        self.dialog_queue = dialog_queue
        self.current_perception = current_perception
        self.messages = [
            {"role": "system", "content": systemPrompt()},
        ]
        self.summarize_time = 0
        self.global_goal = ""
        self.current_goal = ""
        
        # 确保日志目录存在
        if not os.path.exists(settings.CHAT_LOG_DIR):
            os.makedirs(settings.CHAT_LOG_DIR)
        # 根据时间戳命名日志文件
        self.base_log_file = os.path.join(settings.CHAT_LOG_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")
        self.chat_log_file = self.base_log_file.split(".")[0] + "_" + str(0) + ".txt"
        self.log_file_prompt = os.path.join(settings.LOGS_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")
        
        # 调试日志文件
        self.debug_log_file = os.path.join(settings.LOGS_DIR, "debug.log")

        # 清空debug.log
        with open(self.debug_log_file, "w", encoding="utf-8") as log:
            log.write("")
        
        # 添加线程管理
        self.current_thread = None
        self.abort_event = threading.Event()
        self.thread_lock = threading.Lock()
        
        # 状态管理
        self.is_summarizing = False
        self.is_processing_command = False
        self.initial_planning_done = False

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
                return

    def createMessageOnce(self, messages):
        self.debug_log(f"[Model] Calling create_chat_completion_once with {len(messages)} messages")
        try:
            full_message = self.model.create_chat_completion_once(
                messages=messages,
            )
            self.debug_log(f"[Model] Got response: {len(full_message) if full_message else 0} characters")
            return full_message
        except Exception as e:
            self.debug_log(f"[Model] Error in create_chat_completion_once: {e}")
            return None

    def processStreamAsync(self, user_message):
        """异步处理用户命令，立即返回，不阻塞调用方"""
        if self.is_processing_command:
            self.dialog_queue.put_dialog("正在处理上一个命令，请稍候...")
            return
        
        self.is_processing_command = True
        threading.Thread(target=self._processCommand, args=(user_message,), daemon=True).start()

    def _processCommand(self, user_message):
        """内部命令处理"""
        try:
            self.processStream(user_message)
        finally:
            self.is_processing_command = False

    def processStream(self, user_message):

        if settings.ENABLE_INITIAL_PLANNING:
            # 如果还在等待初始规划完成，直接返回
            if not self.initial_planning_done and self.global_goal != "":
                self.dialog_queue.put_dialog("正在等待初始规划完成...")
                return
            
            if self.global_goal == "":
                self.dialog_queue.put_dialog("Formulating a plan for: " + user_message)
                self.global_goal = user_message
                
                # 异步启动初始规划，等待规划完成后才开始推理
                self.debug_log("[Task] Starting initial planning (asynchronous)...")
                self._start_initial_planning_async()
                
                self.dialog_queue.put_dialog("Formulating a plan, please wait...")
                
                # 等待规划完成后再继续，不设置临时messages
                return

            # surroundings = self.toolExecutor.executeTool(parse_assistant_message("<check_surroundings></check_surroundings>")[0])
            # inventory = self.toolExecutor.executeTool(parse_assistant_message("<check_inventory></check_inventory>")[0])
            # stream_input = f"{surroundings}\nYou have: \n{inventory}\n\n{user_message}"

        if len(self.messages) > settings.MAX_MESSAGE_LENGTH:
            self.debug_log(f"[Task] Message length exceeded ({len(self.messages)} > {settings.MAX_MESSAGE_LENGTH})")
            # 检查是否已经在总结中，避免重复触发
            if not self.is_summarizing:
                self.debug_log("[Task] Triggering new summarize task")
                self._start_summarize_task_async()
                self.debug_log("[Task] Summarize triggered, continuing with current message processing")
            else:
                self.debug_log("[Task] Summarize already in progress, skipping duplicate trigger")
        
        self.append_to_messages({"role": "user", "content": user_message})

        # 启动推理线程
        if self.current_thread and self.current_thread.is_alive():
            self.abort_event.set()
            self.current_thread.join(timeout=1.0)
        
        self.abort_event.clear()
        self.current_thread = threading.Thread(target=self._processStreamInternal, daemon=True)
        self.current_thread.start()
    
    def _processStreamInternal(self):
        """执行推理逻辑"""
        if self.abort_event.is_set():
            return
        
        full_message = ""
        
        for content_chunk in self.createMessage(self.abort_event):
            if self.abort_event.is_set():
                return
            # print(content_chunk, end="", flush=True)
            full_message += content_chunk
        
        if self.abort_event.is_set():
            return
        
        self.append_to_messages({"role": "assistant", "content": full_message})
        
        content_blocks, has_tool_use = parse_assistant_message(full_message)
        self.add_to_dialog_queue(content_blocks)
        result = self.toolExecutor.executeTool(content_blocks)
        
        if result and not self.abort_event.is_set():
            self.append_to_messages({"role": "user", "content": result})
            self._processStreamInternal()

    def append_to_messages(self, message):
        self.messages.append(message)
        self.write_chat_log(message)
        
    def write_chat_log(self, message):
        timestamp = datetime.datetime.now().isoformat()
        with open(self.chat_log_file, "a", encoding="utf-8") as log:
            log.write(f"\n\n[Time] {timestamp} ")
            log.write(message["role"] + "\n" + message["content"])

    def writeLogPrompt(self, text):
        with open(self.log_file_prompt, "a", encoding="utf-8") as log:
            log.write(text + "\n")
    
    def debug_log(self, message):
        """写入调试日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.debug_log_file, "a", encoding="utf-8") as log:
            log.write(f"[{timestamp}] {message}\n")
    
    def is_inference_running(self):
        """检查当前是否有推理正在进行"""
        return self.current_thread is not None and self.current_thread.is_alive()
    
    def abort_current_inference(self):
        """强制终止当前推理"""
        if self.current_thread and self.current_thread.is_alive():
            self.abort_event.set()
            self.current_thread.join(timeout=1.0)
            return True
        return False
    
    def _start_initial_planning_async(self):
        """异步启动初始规划"""
        if self.initial_planning_done:
            return
        threading.Thread(target=self._do_initial_planning, daemon=True).start()
    
    def _do_initial_planning(self):
        """执行初始规划"""
        self.debug_log("[Planning] Starting initial planning")
        
        result = self.summarize_task()
        if result:
            self.debug_log("[Planning] Initial planning completed successfully")
            self.current_goal = result["next_objectives"]
            next_command = f"全局目标：\n{self.global_goal}\n当前目标：\n{result['next_objectives']}\n近期行动回顾：\n{result['recent_actions']}"
            
            # 设置初始的messages
            self.messages = [
                {"role": "system", "content": systemPrompt()}
            ]
            self.append_to_messages({"role": "user", "content": next_command})
            self.debug_log("[Planning] Initial messages set with planning result")
            
            self.dialog_queue.put_dialog("初始计划制定完成！开始执行任务...")
        else:
            self.debug_log("[Planning] Initial planning failed, using default strategy")
            # 即使规划失败，也要设置基本的messages
            next_command = f"全局目标：\n{self.global_goal}\n\n请开始执行任务。"
            self.messages = [
                {"role": "system", "content": systemPrompt()}
            ]
            self.append_to_messages({"role": "user", "content": next_command})
            self.dialog_queue.put_dialog("使用默认策略开始")
        
        self.initial_planning_done = True
        self._start_execution()
    
    def _start_execution(self):
        """开始任务执行"""
        self.debug_log("[Execution] Starting task execution")
        if self.current_thread and self.current_thread.is_alive():
            self.debug_log("[Execution] Already running, skipping")
            return
        
        self.abort_event.clear()
        self.current_thread = threading.Thread(target=self._processStreamInternal, daemon=True)
        self.current_thread.start()
        self.debug_log("[Execution] Task execution thread started")
    
    def _restart_inference_after_summarize(self):
        """总结完成后重新启动推理"""
        self.debug_log("[Summarize] Restarting inference after summarize completion")
        if self.current_thread and self.current_thread.is_alive():
            self.abort_event.set()
            self.current_thread.join(timeout=1.0)
        
        self.abort_event.clear()
        self.current_thread = threading.Thread(target=self._processStreamInternal, daemon=True)
        self.current_thread.start()
        
    def add_to_dialog_queue(self, content_blocks):
        for block in content_blocks:
            if block.get('type') == 'text':
                self.dialog_queue.put_dialog(block["content"])
            if block.get('type') == 'tool_use' and block.get('name') == "task_completion":
                self.dialog_queue.put_dialog("Task Complete:" + block["params"].get("result", ""))
    
    def _start_summarize_task_async(self):
        """异步启动总结任务"""
        self.debug_log(f"[Summarize] Request to start summarize task, current state: is_summarizing={self.is_summarizing}")
        if self.is_summarizing:
            self.debug_log("[Summarize] Already summarizing, ignoring request")
            return
        
        self.is_summarizing = True
        self.debug_log(f"[Summarize] Starting new summarize thread for {len(self.messages)} messages")
        threading.Thread(target=self._do_summarize, daemon=True).start()
    
    def _do_summarize(self):
        """执行总结任务"""
        try:
            self.debug_log(f"[Summarize] Starting summarize task, message count: {len(self.messages)}")
            result = self.summarize_task()
            
            if result:
                self.debug_log(f"[Summarize] Summarize task completed successfully")
                if "next_objectives" in result:
                    self.current_goal = result["next_objectives"]
                    self.debug_log(f"[Summarize] Updated current goal: {self.current_goal[:50]}...")
                
                # 重置messages并使用总结结果
                next_command = f"全局目标：\n{self.global_goal}\n当前目标：\n{result['next_objectives']}\n当前状态：\n{result['current_situation']}\n近期行动回顾：\n{result['recent_actions']}"
                self.messages = [
                    {"role": "system", "content": systemPrompt()}
                ]
                self.append_to_messages({"role": "user", "content": next_command})
                self.debug_log("[Summarize] Messages reset with summary result")
                
                # 重新开始推理流程
                self._restart_inference_after_summarize()
                
                self.dialog_queue.put_dialog("策略更新完成，重新开始推理")
            else:
                self.debug_log("[Summarize] Warning: Summarize task returned empty result")
                self.dialog_queue.put_dialog("策略更新遇到问题")
        
        except Exception as e:
            self.debug_log(f"[Summarize] Error in summarize task: {e}")
            self.dialog_queue.put_dialog(f"策略更新出错: {str(e)}")
        
        finally:
            self.is_summarizing = False
            self.debug_log("[Summarize] Summarize task finished")


    def summarize_task(self):
        self.debug_log(f"[Summarize] Starting summarize_task #{self.summarize_time + 1}")
        self.summarize_time += 1
        
        try:
            role_status = self.toolExecutor.check_status()
            world_status = json.dumps(self.current_perception["WorldStatus"], indent=4, ensure_ascii=False)
            history_actions = self.format_history()
            possessions = self.toolExecutor.executeTool(parse_assistant_message("<check_inventory></check_inventory>")[0])
            
            self.debug_log(f"[Summarize] Preparing summarize prompt...")
            prompt_for_summarize = instruction_summarize(
                global_goal=self.global_goal, 
                last_goal=self.current_goal, 
                role_status=role_status, 
                possessions=possessions, 
                world_status=world_status, 
                history_actions=history_actions
            )
            
            messages = [
                {"role": "system", "content": system_prompt_summarize()},
                {"role": "user", "content": prompt_for_summarize}
            ]
            
            self.debug_log(f"[Summarize] Calling AI model for summary...")
            summary = self.createMessageOnce(messages)
            
            if not summary:
                self.debug_log("[Summarize] Error: AI model returned empty summary")
                return None
            
            self.debug_log(f"[Summarize] AI model returned summary: {len(summary)} characters")
            result = self.parse_summary(summary)
            
            if result:
                self.debug_log(f"[Summarize] Parsed result successfully: {list(result.keys())}")
                self.writeLogPrompt(json.dumps(result, indent=4, ensure_ascii=False))
            else:
                self.debug_log("[Summarize] Error: Failed to parse summary result")
            
            self.chat_log_file = self.base_log_file.split(".")[0] + "_" + str(self.summarize_time) + ".txt"
            return result
            
        except Exception as e:
            self.debug_log(f"[Summarize] Exception in summarize_task: {e}")
            return None

    def format_history(self):
        history = ""
        for i, message in enumerate(self.messages):
            if i <= 1:
                continue
            if message["role"] == "assistant":
                history += "\n" + "[Assistant]\n" + message["content"] + "\n"
            elif message["role"] == "user":
                history += "\n" + "[Environment]\n" + message["content"] + "\n"
        self.writeLogPrompt(history)
        return history

    def parse_summary(self, summary):
        """
        解析总结文档的三个部分：近期行动回顾、当前局势分析、下阶段目标
        
        Args:
            summary (str): 总结文档内容
            
        Returns:
            dict: 包含三个部分文本内容的字典
        """
        result = {
            "recent_actions": "",
            "current_situation": "",
            "next_objectives": ""
        }
        
        # 1. 提取近期行动回顾
        recent_actions_match = re.search(r'## 1\. 近期行动回顾\s*```text\s*(.*?)\s*```', summary, re.DOTALL)
        if recent_actions_match:
            result["recent_actions"] = recent_actions_match.group(1).strip()
        
        # 2. 提取当前局势分析
        situation_match = re.search(r'## 2\. 当前局势分析\s*```text\s*(.*?)\s*```', summary, re.DOTALL)
        if situation_match:
            result["current_situation"] = situation_match.group(1).strip()
        
        # 3. 提取下阶段目标
        objectives_match = re.search(r'## 3\. 下阶段目标\s*```text\s*(.*?)\s*```', summary, re.DOTALL)
        if objectives_match:
            result["next_objectives"] = objectives_match.group(1).strip()
        
        return result