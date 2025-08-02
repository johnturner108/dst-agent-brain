import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import logging
from parse_tool import parse_assistant_message
from task import Task
import threading
from prompt import systemPrompt
from queue import Queue, Empty
from tool_executor import parse_action_str

# 配置日志，方便在终端看到服务器活动
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 服务器配置 ---
HOST_NAME = "localhost"
SERVER_PORT = 8081


# --- HTTP 请求处理类 ---
class SimpleAIHandler(BaseHTTPRequestHandler):
    

    def __init__(self, request, client_address, server, action_queue, current_perception, task_instance):
        self.action_queue = action_queue
        self.current_perception = current_perception
        self.task_instance = task_instance
        super().__init__(request, client_address, server)

    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def do_GET(self):
        # 尝试匹配 /GUID/decide/Behaviour 路径
        match = re.match(r'/(\d+)/decide/(Behaviour|Dialog)', self.path)

        if match:
            guid = match.group(1)
            layer = match.group(2)
            # logging.info(f"Received GET request: GUID={guid}, Layer={layer}")

            if layer == "Behaviour":
                response_data = self.action_queue.get_action()
                # logging.info(f"Responding with Behaviour Action: {response_data}")
                self._set_headers()
                self.wfile.write(json.dumps(response_data, sort_keys=True).encode("utf-8"))
                
            elif layer == "Dialog":

                logging.info(f"LLM 响应已完成。")
                response_data = {"Type": "Speak", "Utterance": "Hello from simple AI!"}
                logging.info(f"Responding with Dialog Utterance: {response_data['Utterance']}")
                self._set_headers()
                self.wfile.write(json.dumps(response_data, sort_keys=True).encode("utf-8"))
            else:
                # 理论上不会走到这里，因为正则已经限制了 layer
                self._set_headers(404, 'text/plain')
                self.wfile.write(b"Not Found")
                return
        
        elif self.path == "/stats":
            # 添加统计信息端点
            stats = self.action_queue.get_stats()
            self._set_headers()
            self.wfile.write(json.dumps(stats, sort_keys=True).encode("utf-8"))
        
        elif self.path == "/inference-status":
            # 添加推理状态检查端点
            status = {
                "inference_running": self.task_instance.is_inference_running(),
                "abort_event_set": self.task_instance.abort_event.is_set()
            }
            self._set_headers()
            self.wfile.write(json.dumps(status, sort_keys=True).encode("utf-8"))
        
        elif self.path == "/abort-inference":
            # 添加强制终止推理端点
            aborted = self.task_instance.abort_current_inference()
            response = {"aborted": aborted}
            self._set_headers()
            self.wfile.write(json.dumps(response, sort_keys=True).encode("utf-8"))

        elif self.path == "/vision":
            self._set_headers()
            self.wfile.write(json.dumps(self.current_perception, sort_keys=True).encode("utf-8"))

        else:
            # 对于不匹配 /GUID/decide/(Behaviour|Dialog) 的 GET 请求，返回 404
            logging.warning(f"Unhandled GET request path: {self.path}")
            self._set_headers(404, 'text/plain')
            # self.wfile.write(b"Not Found")

    def do_POST(self):
        # 获取 POST 请求的体内容长度
        content_length = int(self.headers.get('Content-Length', 0))
        # 读取请求体
        post_data_raw = self.rfile.read(content_length)

        try:
            # 尝试解码 JSON 数据
            post_data = json.loads(post_data_raw.decode('utf-8'))
            # 打印解析后的 JSON 数据


            # logging.info(f"Received POST body (JSON): {json.dumps(post_data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            # 如果不是有效的 JSON，则打印原始数据
            logging.error(f"Received POST body (NOT JSON): {post_data_raw.decode('utf-8', errors='ignore')}")
            self._set_headers(400, 'text/plain')
            self.wfile.write(b"Bad Request: Invalid JSON")
            return

        # 匹配 /GUID/perceptions 或 /GUID/events 路径
        match_perceptions = re.match(r'/(\d+)/perceptions', self.path)
        match_events = re.match(r'/(\d+)/events', self.path)
        match_command = re.match(r'/(\d+)/command', self.path)

        if match_perceptions:
            self.current_perception.clear() # 清空旧数据
            self.current_perception.update(post_data) # 更新全局字典
            guid = match_perceptions.group(1)
            self._set_headers(202, 'application/json') # 202 Accepted is perfect here
            response = {"status": f"Perception for GUID {guid} received and is being processed."}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        elif match_events:
            guid = match_events.group(1)
            if post_data["Type"] == "Action-End" or post_data["Type"] == "Action-Failed":
                # 直接调用processStream，它会内部管理线程
                self.task_instance.processStream(json.dumps(post_data))
            logging.info(f"Path matched: /GUID/events for GUID {guid}")
            logging.info(post_data)
            self._set_headers()
            self.wfile.write(json.dumps({"status": "received event"}).encode("utf-8"))
        elif match_command:
            guid = match_command.group(1)
            # user_message = post_data["command"] + json.dumps(current_perception)
            user_message = post_data["command"]
            # print(user_message)
            # 直接调用processStream，它会内部管理线程
            self.task_instance.processStream("The current entities are surrounding you:\n" + self.task_instance.toolExecutor.executeTool(parse_assistant_message("<check_surroundings></check_surroundings>")[0])  + user_message)

            # 立即响应客户端，告诉它命令已接受
            logging.info(f"Command for GUID {guid} is processing in background.")
            self._set_headers(202, 'application/json') # 202 Accepted is perfect here
            response = {"status": f"Command for GUID {guid} received and is being processed."}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            logging.warning(f"Unhandled POST request path: {self.path}")
            self._set_headers(404, 'text/plain')
            self.wfile.write(b"Not Found or Not Handled")



    # 可以选择性地禁用或简化默认的日志信息，以保持终端干净
    def log_message(self, format, *args):
        # logging.debug(format % args) # 这样可以禁用默认的 HTTP server 日志，只看我们自己的 logging.info
        pass # 完全禁用默认日志，只看我们自己的 logging.info

current_perception = {}


class ActionQueue:
    """动作队列管理器，实现生产者-消费者模式"""
    
    def __init__(self, maxsize=10):
        self.queue = Queue(maxsize=maxsize)
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'produced': 0,
            'consumed': 0,
            'dropped': 0
        }
    
    def put_action(self, action: dict) -> bool:
        """
        生产者：AI添加动作到队列
        返回True表示成功添加，False表示队列已满
        """
        try:
            with self.lock:
                if self.queue.full():
                    self.stats['dropped'] += 1
                    self.logger.warning(f"Action queue is full, dropping action: {action}")
                    return False
                
                self.queue.put(action, timeout=1.0)
                self.stats['produced'] += 1
                self.logger.info(f"Action added to queue: {action.get('Action', 'Unknown')}")
                return True
        except Exception as e:
            self.logger.error(f"Error adding action to queue: {e}")
            return False
    
    def get_action(self, timeout=1.0) -> dict:
        """
        消费者：客户端从队列获取动作
        如果队列为空，返回空字典
        """
        try:
            action = self.queue.get(timeout=timeout)
            with self.lock:
                self.stats['consumed'] += 1
            self.logger.info(f"Action consumed from queue: {action.get('Action', 'Unknown')}")
            return action
        except Empty:
            self.logger.debug("No action available in queue")
            return {}
        except Exception as e:
            self.logger.error(f"Error getting action from queue: {e}")
            return {}
    
    def clear_queue(self):
        """清空队列"""
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            self.logger.info("Action queue cleared")
    
    def get_stats(self) -> dict:
        """获取队列统计信息"""
        with self.lock:
            return {
                'queue_size': self.queue.qsize(),
                'max_size': self.queue.maxsize,
                'stats': self.stats.copy()
            }
    
    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue.empty()
    
    def is_full(self) -> bool:
        """检查队列是否已满"""
        return self.queue.full()

        
# current_action = {
#     "Type": "Action",
#     "Action": "BUILD",
#     "InvObject": "-",
#     "Recipe": "sciencemachine",
#     "Name": "Action(BUILD, -, 50, 75, sciencemachine)",
#     "PosX": 50,
#     "Target": "-",
#     "PosZ": 75,
#     "WFN": "Action(BUILD, -, 50, 75, sciencemachine)"
# }
# current_action = {}
action_queue = ActionQueue(maxsize=10)
# action_queue.put_action(parse_action_str("Action(DROP, [berries_GUID], -, -, -) = -"))
# task_instance 也只创建一次
# task_instance = Task(current_action, current_perception)
task_instance = Task(action_queue, current_perception)
def run_server():
    # Factory function to create handlers with the shared state
    def handler_factory(*args, **kwargs):
        # Pass the global state and the task instance to the handler
        return SimpleAIHandler(*args, **kwargs, action_queue=action_queue, current_perception=current_perception, task_instance=task_instance)

    # Use the custom factory to instantiate the server
    webServer = HTTPServer((HOST_NAME, SERVER_PORT), handler_factory)
    logging.info(f"Server started at http://{HOST_NAME}:{SERVER_PORT}")
    logging.info("Awaiting requests...")

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    logging.info("Server stopped.")

# --- 当脚本直接运行时执行主函数 ---
if __name__ == "__main__":
    run_server()