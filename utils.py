from queue import Queue, Empty
import threading
import logging

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
    

class DialogQueue:

    def __init__(self, maxsize=10):
        self.queue = Queue(maxsize=maxsize)
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'produced': 0,
            'consumed': 0,
            'dropped': 0
        }
    
    def put_dialog(self, dialog: str) -> bool:

        try:
            with self.lock:
                if self.queue.full():
                    self.stats['dropped'] += 1
                    return False
                
                self.queue.put(dialog, timeout=1.0)
                self.stats['produced'] += 1
                self.logger.info(f"Dialog added to queue: {dialog}")
                return True
        except Exception as e:
            self.logger.error(f"Error adding dialog to queue: {e}")
            return False
    
    def get_dialog(self, timeout=1.0) -> str:

        try:
            dialog = self.queue.get(timeout=timeout)
            with self.lock:
                self.stats['consumed'] += 1
            self.logger.info(f"Dialog consumed from queue: {dialog}")
            return dialog
        except Empty:
            self.logger.debug("No dialog available in queue")
            return ""
        except Exception as e:
            self.logger.error(f"Error getting dialog from queue: {e}")
            return ""
    
    def clear_queue(self):
        """清空队列"""
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
            self.logger.info("Dialog queue cleared")
    
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