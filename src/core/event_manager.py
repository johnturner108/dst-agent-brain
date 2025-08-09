class EventManager:
    """
    事件管理器，负责处理游戏中的各种事件
    """
    
    def __init__(self, task_instance, current_perception):
        """
        初始化事件管理器
        current_perception: 当前感知字典
        Args:
            task_instance: Task实例，用于调用processStream方法
        """
        self.task_instance = task_instance
        self.current_perception = current_perception

    def handle_event(self, data):
        """
        处理接收到的事件数据
        
        Args:
            data: 事件数据字典
        """
        info = "Info: {}".format(data.get("Info")) if data.get("Info") else ""
        
        # 处理BUILD相关事件
        if "BUILD" in data.get("Name"):
            self._handle_build_event(data, info)
        # 处理PATHFIND事件
        elif "PATHFIND" in data.get("Name"):
            self._handle_pathfind_event(data)
        # 处理其他一般事件
        else:
            self._handle_general_event(data, info)
        
        # 处理属性变化事件
        self._handle_property_change_events(data)
    
    def _handle_build_event(self, data, info):
        """处理BUILD相关事件"""
        if data.get("Type") == "Action-Failed":
            # print(info)
            self.task_instance.processStream(
                "The action {} -> {} failed. {}".format(
                    data.get("Name"), data.get("Value"), info
                )
            )
        elif data.get("Type") in "Action-End":
            self.task_instance.processStream(
                "The action {} -> {} done. {}".format(
                    data.get("Name"), data.get("Value"), info
                )
            )
    
    def _handle_pathfind_event(self, data):
        """处理PATHFIND事件"""
        if self.task_instance.toolExecutor._has_pathfind_action():
            # print(f"[EventManager] Pathfind event received, stopping pathfind thread")
            self.task_instance.toolExecutor.pathfind_stop_event.set()
            # Wait briefly for the old thread to finish
            self.task_instance.toolExecutor.pathfind_thread.join(timeout=1)
        if data.get("Type") in "Action-End":
            self.task_instance.processStream(
                "You've arrived at " + str(data.get("Value"))
            )
        else:
            self.task_instance.processStream(
                "Can't find way to " + str(data.get("Value")) + "or is interuppted" + "Your current location is x: {}, z: {}".format(self.current_perception["PosX"], self.current_perception["PosZ"])
            )
    
    def _handle_general_event(self, data, info):
        """处理一般事件"""
        if data.get("Type") in "Action-End":
            self.task_instance.processStream(
                "The action {} -> {} done. {}".format(
                    data.get("Name"), data.get("Value"), info
                )
            )
        elif data.get("Type") == "Action-Failed":
            self.task_instance.processStream(
                "The action {} -> {} failed. {}".format(
                    data.get("Name"), data.get("Value"), info
                )
            )
    
    def _handle_property_change_events(self, data):
        """处理属性变化事件"""
        # 处理光照变化
        if data.get("Type") == "Property-Change" and data.get("Name") == "InLight(Walter)":
            if data.get("Value") == "True":
                self.task_instance.processStream("You are in light now.")
            else:
                self.task_instance.processStream("You are in dark now.")
        
        # 处理夜晚来临
        if data.get("Type") == "Property-Change" and data.get("Name") == "EnteringNight":
            if data.get("Value") == "True":
                # print(data)
                exploration_stop = ""
                pathfind_stop = ""
                if self.task_instance.toolExecutor._has_explore_action():
                    self.task_instance.toolExecutor.observer_stop_event.set()
                    # Wait briefly for the old thread to finish
                    self.task_instance.toolExecutor.observer_thread.join(timeout=0.5)
                    exploration_stop = "[Exploration Stopped]\n"
                elif self.task_instance.toolExecutor._has_pathfind_action():
                    self.task_instance.toolExecutor.pathfind_stop_event.set()
                    # Wait briefly for the old thread to finish
                    self.task_instance.toolExecutor.pathfind_thread.join(timeout=0.5)
                    pathfind_stop = "[Pathfind Stopped]\n"

                self.task_instance.processStream(
                    exploration_stop + pathfind_stop +
                    "You are about to enter night. Make sure you have a light source like a torch etc. "
                    "You have to equip the light source to prevent you from being attacked by Charlie."
                ) 