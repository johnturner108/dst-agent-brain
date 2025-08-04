import re
import json
import os
import threading
import time
import uuid

def parse_action_str(action_str):
    # 解析动作字符串以提取动作类型 (Action) 和操作对象 (InvObject)
    # 示例：Action(BUILD, -, -, -, axe)
    action_match = re.match(r'Action\(([^,]+),\s*(\d+|-),\s*([^,]+),\s*([^,]+),\s*([^,]+)\)\s*=\s*(\d+|-)', action_str)
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
    # 生成一个4位数的uuid作为action的唯一标识
    auid = str(uuid.uuid4())[:4]
    action_obj = {
        "Type": "Action",
        "Action": action_type,
        "InvObject": inv_object,
        "Recipe": recipe,
        "Name": action_str, # 使用完整的动作字符串作为 Name
        "PosX": posX,
        "Target": target,
        "PosZ": posZ,
        "WFN": action_str, # 使用完整的动作字符串作为 WFN
        "AUID": auid # 使用完整的动作字符串作为 AUID
    }
    return action_obj
    

class ToolExecutor:
    """
    ToolExecutor 类负责根据大型语言模型 (LLM) 返回的工具使用指令，
    更新应用程序的全局状态（即 current_action 字典）。
    """
    def __init__(self, task_instance, action_queue, shared_perception_dict, dialog_queue, self_uid):
        self.task_instance = task_instance
        self.action_queue = action_queue
        self.dialog_queue = dialog_queue
        self.shared_perception_dict = shared_perception_dict
        self.map_file_path = './memory/map.json'
        self.map = self.load_map() # 初始化时从文件加载地图
        self.self_uid = self_uid
        self.observed_guids = []
        self.start_cleanup_timer()  # 启动定时清理
        print(f"ToolExecutor 初始化，动作队列: {self.action_queue} 和 感知字典：{self.shared_perception_dict}")

        # Add attributes for managing the observer thread
        self.observer_thread = None
        self.observer_stop_event = threading.Event()
    
    def clear_observed_guids(self):
        print("Clearing observed_guids...")
        self.observed_guids.clear()  # 清空集合
        self.start_cleanup_timer()  # 递归调用，实现循环

    def start_cleanup_timer(self):
        timer = threading.Timer(120, self.clear_observed_guids)
        timer.daemon = True  # 设为守护线程（主线程退出时自动结束）
        timer.start()
    
    def load_map(self):
        """
        从 memory/map.json 文件加载地图数据。如果文件不存在，则创建空文件并返回空字典。
        """
        if not os.path.exists('./memory'):
            os.makedirs('./memory')
        
        if os.path.exists(self.map_file_path):
            with open(self.map_file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print(f"警告: {self.map_file_path} 文件内容为空或格式不正确，将初始化为空字典。")
                    return {}
        else:
            # 文件不存在，创建空文件并返回空字典
            with open(self.map_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}

    def save_map(self):
        """
        将当前地图数据保存到 memory/map.json 文件中。
        """
        with open(self.map_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.map, f, ensure_ascii=False, indent=4)

    def executeTool(self, content_blocks):

        # print(f"正在执行工具，内容块: {content_blocks}")
        for block in content_blocks:
            # 检查当前块是否是类型为 'tool_use' 且名称为 'perform_action' 的工具指令
            if block.get('type') == 'tool_use':
                action_name = block.get('name')
                if action_name == 'perform_action':
                    return self.execute_perform_action(block)
                elif action_name == 'check_inventory':
                    return self.execute_check_inventory(block)
                elif action_name == 'check_equipslots':
                    fields_to_keep = {"GUID", "Prefab"}
                    inventory = [
                        {key: item[key] for key in fields_to_keep if key in item}
                        for item in self.shared_perception_dict["EquipSlots"]
                    ]
                    return "You are equipped with:\n" + json.dumps(inventory, sort_keys=True)
                elif action_name == 'check_surroundings':
                    fields_to_keep = {"GUID", "Hammerable", "Mineable", "Choppable", "Collectable", "Quantity", "Prefab", "X", "Z"}
                    inventory = [
                        {key: item[key] for key in fields_to_keep if key in item}
                        for item in self.shared_perception_dict["Vision"]
                    ]
                    return "There are the following entities near you:\n" + json.dumps(inventory, sort_keys=True)
                elif action_name == 'task_completion':
                    return
                elif action_name == 'mark_loc':
                    loc_name = block.get('params')['name']
                    self.map[loc_name] = json.dumps(block.get('params'))
                    self.save_map() # 在标记位置后保存地图
                    return "The location {} has been marked".format(loc_name)
                elif action_name == 'check_map':
                    return "The map has the following locations:\n" + json.dumps(self.map, sort_keys=True)
                elif action_name == 'check_self_GUID':
                    return "You GUID is: " + str(self.self_uid)
                elif action_name == 'observer':
                    return self.execute_observer(block)

        print("在内容块中未找到 'perform_action' 工具使用指令。")


    def execute_observer(self, block):
        """
        Starts a background thread to observe for a specific item.
        """
        # Stop any previously running observer thread
        if self.observer_thread and self.observer_thread.is_alive():
            self.observer_stop_event.set()
            # Wait briefly for the old thread to finish
            self.observer_thread.join(timeout=1.0) 

        params = block.get('params', {})
        item_to_find = params.get('entities')

        if not item_to_find:
            return "Observer Error: You must specify the 'entities' to observe."

        # Clear the stop event for the new thread
        self.observer_stop_event.clear()
        
        # Create and start the new observer thread
        self.observer_thread = threading.Thread(
            target=self._observe_loop, 
            args=(item_to_find,),
            daemon=True  # Daemon threads exit when the main program exits
        )
        self.observer_thread.start()

        # Return a confirmation message to the LLM
        return f"Observer has been set up. I will now monitor the surroundings for '{item_to_find}' and will notify you when it appears."

    def _observe_loop(self, entities_str: str):
        """
        The actual loop that runs in the background thread.
        """
        entity_list = [name.strip() for name in entities_str.split(',') if name.strip()]
        print(f"[Observer] Started looking for item: '{entities_str}'")
        while not self.observer_stop_event.is_set():
            try:
                # Safely get the list of visible items
                vision_items = self.shared_perception_dict.get("Vision", [])
                
                if not vision_items:
                    time.sleep(1) # Wait if perception data is not yet available
                    continue
                
                found_item_list = []
                for item in vision_items:
                    found_item_name = item.get("Prefab")
                    if item and item.get("Prefab") in entity_list:
                        print(f"[Observer] Found '{found_item_name}'! Triggering new inference.")
                        self.observed_guids.append(item.get("GUID"))
                        found_item_list.append(found_item_name)

                
                if len(found_item_list) > 0:
                    # Construct the new prompt for the LLM
                    prompt = (f"Observer Shutting down: The item you were waiting for, '{json.dumps(found_item_list)}', "
                                f"is now in your surroundings. You can proceed with the next action. You may set up the observer again if you are done with your action.")
                    
                    # Use the stored task_instance to call processStream
                    self.task_instance.processStream(prompt)
                    self.action_queue.put_action(parse_action_str("Action(STOP, -, -, -, -) = -"))
                    self.dialog_queue.put_dialog(f"I found {json.dumps(found_item_list)}")
                    # Job is done, exit the thread
                    return 
                
                # Wait for 1 second before checking again to avoid high CPU usage
                time.sleep(1)

            except Exception as e:
                print(f"[Observer] Error in observation loop: {e}")
                time.sleep(5) # Wait longer if an error occurs

        print(f"[Observer] Stopped for '{entities_str}'.")


    
    def execute_perform_action(self, block):

        params = block.get('params', {}) # 获取工具指令的参数
        if "\n" in params.get('action'):
            action_strs = params.get('action').split("\n")
            for action_str in action_strs:
                action_obj = parse_action_str(action_str)
                if type(action_obj) is str:
                    return action_obj
                self.action_queue.put_action(action_obj)
        else:
            action_str = params.get('action') # 例如：'Action(BUILD, -, -, -, axe)'
            action_obj = parse_action_str(action_str)
            if type(action_obj) is str:
                return action_obj
            self.action_queue.put_action(action_obj)
        # requires_approval = params.get('requires_approval') # 这个参数当前未在 current_action 中使用
        if action_obj.get("Action") == "PATHFIND":
            return "You are on your way now, output <wait><\wait> if you have nothing to do while the character goes towards the destination."
        if action_obj.get("Action") == "CHOP":
            return "You are now Chopping, send next action to the action queue if you want. (Just plan the next action or the next few actions, better not plan too far ahead)"
        return # "The actions are being performed right now."# 执行第一个工具使用块后即返回，因为用户要求“中止”
    
    def execute_check_inventory(self, block):
        if block.get('params') == {}:
            fields_to_keep = {"GUID", "Quantity", "Prefab"}
            # item可能为空，需要处理
            inventory = [
                {key: item[key] for key in fields_to_keep if item and key in item}
                for item in self.shared_perception_dict["ItemSlots"]
            ]
            equips = [
                {key: item[key] for key in fields_to_keep if item and key in item}
                for item in self.shared_perception_dict["EquipSlots"]
            ]
            return "Your current inventory has the following items:\n" + json.dumps(inventory, sort_keys=True) + '\n' \
                    + "And you are equipped with:\n" + json.dumps(equips, sort_keys=True)
        else:
            item_name = block.get('params')['item_name']
            quantity_itemslots = 0
            # print(self.shared_perception_dict["ItemSlots"])
            for item in self.shared_perception_dict["ItemSlots"]:
                if item and item["Prefab"] == item_name:
                    quantity_itemslots += item.get("Quantity", 0)
            quantity_equipslots = 0
            # print(self.shared_perception_dict["EquipSlots"])
            for item in self.shared_perception_dict["EquipSlots"]:
                if item and item["Prefab"] == item_name:
                    quantity_equipslots += item.get("Quantity", 0)
            
            itemslots_response = "Your have {} {} in your ItemSlots.".format(quantity_itemslots, item_name, ) if quantity_itemslots > 0 else ""
            equipslots_response = "Your have {} {} in your EquipSlots.".format(quantity_equipslots, item_name, ) if quantity_equipslots > 0 else ""

            return itemslots_response + "\n" + equipslots_response