import re
import json
import os
import threading
import time
import uuid
from ..config.settings import settings

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
        self.map_file_path = settings.MAP_FILE_PATH
        self.map = self.load_map() # 初始化时从文件加载地图
        self.self_uid = self_uid
        self.observed_guids = []
        self.start_cleanup_timer()  # 启动定时清理
        print(f"ToolExecutor 初始化，动作队列: {self.action_queue} 和 感知字典：{self.shared_perception_dict}")

        # Add attributes for managing the observer thread
        self.observer_thread = None
        self.observer_stop_event = threading.Event()
        self.pathfind_thread = None
        self.pathfind_stop_event = threading.Event()
        # 初始化时从文件加载recipe_list
        self.recipe_to_ingredients = self.load_recipe_to_ingredients()
    
    def load_recipe_to_ingredients(self):
        with open(settings.RECIPE_LIST_FILE_PATH, 'r', encoding='utf-8') as f:
            recipe_list = json.load(f)
        recipe_to_ingredients = {}
        for recipe in recipe_list:
            recipe_to_ingredients[recipe["name"]] = recipe["ingredients"]
            recipe_to_ingredients[recipe["product"]] = recipe["ingredients"]
            recipe_to_ingredients[recipe["display_name_en"]] = recipe["ingredients"]
            recipe_to_ingredients[recipe["display_name_zh"]] = recipe["ingredients"]
        return recipe_to_ingredients
    
    def _has_explore_action(self):
        """检查是否正在探索（观察者线程是否在运行）"""
        return self.observer_thread is not None and self.observer_thread.is_alive()

    def _has_pathfind_action(self):
        """检查是否正在探索（观察者线程是否在运行）"""
        return self.pathfind_thread is not None and self.pathfind_thread.is_alive()
    
    def clear_observed_guids(self):
        print("Clearing observed_guids...")
        self.observed_guids.clear()  # 清空集合
        self.start_cleanup_timer()  # 递归调用，实现循环

    def start_cleanup_timer(self):
        timer = threading.Timer(settings.OBSERVER_CLEANUP_INTERVAL, self.clear_observed_guids)
        timer.daemon = True  # 设为守护线程（主线程退出时自动结束）
        timer.start()
    
    def load_map(self):
        """
        从配置的地图文件路径加载地图数据。如果文件不存在，则创建空文件并返回空字典。
        """
        # 确保内存目录存在
        if not os.path.exists(settings.MEMORY_DIR):
            os.makedirs(settings.MEMORY_DIR)
        
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
                json.dump({}, f, ensure_ascii=False, indent=4)
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
                if action_name == 'do':
                    return self.execute_do(block)
                elif action_name == 'check_inventory':
                    return self.execute_check_inventory(block)
                elif action_name == 'check_equipslots':
                    fields_to_keep = {"GUID", "Prefab"}
                    inventory = [
                        {key: item[key] for key in fields_to_keep if key in item}
                        for item in self.shared_perception_dict["Possessions"]["EquipSlots"]
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
                # elif action_name == 'observer':
                #     return self.execute_observer(block)
                elif action_name == 'explore':
                    return self.execute_observer(block)
                elif action_name == 'check_recipe':
                    return self.execute_check_recipe(block)
                elif action_name == 'check_status':
                    return self.check_status()
                elif action_name == 'stop_explore':
                    return self.stop_explore()
                elif action_name == 'stop_pathfind':
                    return self.stop_pathfind()

        print("在内容块中未找到工具使用指令。")

    def stop_explore(self):
        if self._has_explore_action():
            self.observer_stop_event.set()
            self.observer_thread.join(timeout=0.5)
            return "Exploration stopped."
        else:
            return "No exploration in progress."
    
    def stop_pathfind(self):
        if self._has_pathfind_action():
            self.pathfind_stop_event.set()
            self.pathfind_thread.join(timeout=0.5)
            return "Pathfinding stopped."
        else:
            return "No pathfinding in progress."

    def execute_check_recipe(self, block):
        if block.get('params') == {}:
            return "You should specify the recipe you want to check."
        elif block.get('params')['recipe'] not in self.recipe_to_ingredients:
            return "Recipe not found"
        else:
            recipe_name = block.get('params')['recipe']
            return "The recipe {} is available.".format(recipe_name) + "\n" + json.dumps(self.recipe_to_ingredients[recipe_name], sort_keys=True, ensure_ascii=False)

    def execute_observer(self, block):
        """
        Starts a background thread to observe for a specific item.
        """
        # 检查是否已经在探索
        if self._has_explore_action():
            print(f"[ToolExecutor] Already exploring, cannot start new observer")
            return "Cannot start observer because exploration is already in progress. Please wait for the current exploration to complete."
        
        # Stop any previously running observer thread
        if self.observer_thread and self.observer_thread.is_alive():
            self.observer_stop_event.set()
            # Wait briefly for the old thread to finish
            self.observer_thread.join(timeout=1.0) 

        params = block.get('params', {})
        item_to_find = params.get('search')

        if not item_to_find:
            return "Observer Error: You must specify the 'search' to look for items."
        self.action_queue.put_action(parse_action_str("Action(EXPLORE, -, -, -, -) = -"))

        
        # Clear the stop event for the new thread
        self.observer_stop_event.clear()
        
        # 延迟1秒
        time.sleep(1) # 延迟一秒，让EXPLORE动作先启动。
        
        # Create and start the new observer thread
        self.observer_thread = threading.Thread(
            target=self._observe_loop, 
            args=(item_to_find,),
            daemon=True  # Daemon threads exit when the main program exits
        )
        self.observer_thread.start()

        # Return a confirmation message to the LLM
        # return f"Observer has been set up. I will now monitor the surroundings for '{item_to_find}' and will notify you when it appears."
        return f"You are now exploring the map, monitoring the surroundings for '{item_to_find}', no `do` tool and explore tool is allowed when exploring."

    def _observe_loop(self, entities_str: str):
        """
        The actual loop that runs in the background thread.
        """

        original_entity_list = [name.strip() for name in entities_str.split(',') if name.strip()]
        entity_list = []
        for name in original_entity_list:
            if name == "cutgrass" and "grass" not in original_entity_list:
                entity_list.append("grass")
            elif name == "grass" and "cutgrass" not in original_entity_list:
                entity_list.append("cutgrass")
            elif name == "twig" and "twigs" not in original_entity_list:
                entity_list.append("twigs")
            elif name == "goldnugget" and "goldnuggets" not in original_entity_list:
                entity_list.append("goldnuggets")
            entity_list.append(name)
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
                    if item and item.get("Prefab") in entity_list and item.get("GUID") not in self.observed_guids:
                        print(f"[Observer] Found '{found_item_name}'! Triggering new inference.")
                        self.observed_guids.append(item.get("GUID"))
                        found_item_list.append({"GUID": item.get("GUID"), "Prefab": found_item_name})

                
                if len(found_item_list) > 0:
                    # Construct the new prompt for the LLM
                    prompt = (f"Observer Shutting down: The item you were waiting for, '{json.dumps(found_item_list)}', "
                                f"is now in your surroundings. You can proceed with the next action. You may set up the observer again if you are done with your action.")
                    
                    # Use the stored task_instance to call processStream
                    self.task_instance.processStream(prompt)
                    self.action_queue.clear_queue()
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


    
    def execute_do(self, block):

        action_obj = parse_action_str(block.get('content'))

        if type(action_obj) is str:
            return action_obj
            
        # 检查是否正在探索
        if self._has_explore_action():
            print(f"[ToolExecutor] Currently exploring, blocking new action: {action_obj.get('Action')}")
            return f"Action '{action_obj.get('Action')}' cannot be added because exploration is currently in progress. Please wait for the exploration to complete or use <stop_explore></stop_explore> to stop the exploration."
        
        if self._has_pathfind_action():
            print(f"[ToolExecutor] Currently going towards the destination, blocking new action: {action_obj.get('Action')}")
            return f"Action '{action_obj.get('Action')}' cannot be added because you are currently going towards the destination. Please wait for the pathfinding to complete or use <stop_pathfind></stop_pathfind> to stop the pathfinding."
        
        # 检查队列大小限制
        if self.action_queue.get_stats()["queue_size"] > settings.ACTION_ALLOWED_NUM:
            return
        
        # 添加动作到队列
        self.action_queue.put_action(action_obj)
        
        # requires_approval = params.get('requires_approval') # 这个参数当前未在 current_action 中使用
        if action_obj.get("Action") == "PATHFIND":
            if self.pathfind_thread and self.pathfind_thread.is_alive():
                self.pathfind_stop_event.set()
                # Wait briefly for the old thread to finish
                self.pathfind_thread.join(timeout=1.0)
            # Clear the stop event for the new thread
            self.pathfind_stop_event.clear()
            # Create and start the new observer thread
            self.pathfind_thread = threading.Thread(
                target=self._pathfind_loop,
                daemon=True  # Daemon threads exit when the main program exits
            )
            self.pathfind_thread.start()
            return "You are on your way now, output <wait><\wait> if you have nothing to do while the character goes towards the destination."
        if action_obj.get("Action") == "CHOP":
            return "You are now Chopping, send next action to the action queue if you want. Or do other stuffs instead."
        return # "The actions are being performed right now."# 执行第一个工具使用块后即返回，因为用户要求"中止"
    
    def _pathfind_loop(self):
        """
        The actual loop that runs in the background thread.
        """
        print(f"[Pathfind] Started going towards the destination")
        while not self.pathfind_stop_event.is_set():
            time.sleep(0.1)
        print(f"[Pathfind] Stopped going towards the destination")

    def execute_check_inventory(self, block):
        if block.get('params') == {}:
            fields_to_keep = {"GUID", "Quantity", "Prefab"}
            # item可能为空，需要处理
            inventory = [
                {key: item[key] for key in fields_to_keep if item and key in item}
                for item in self.shared_perception_dict["Possessions"]["ItemSlots"]
            ]
            equips = [
                {key: item[key] for key in fields_to_keep if item and key in item}
                for item in self.shared_perception_dict["Possessions"]["EquipSlots"]
            ]
            backpack = [
                {key: item[key] for key in fields_to_keep if item and key in item}
                for item in self.shared_perception_dict["Possessions"]["Backpack"]
            ]
            return "Your current inventory has the following items:\n" + json.dumps(inventory, sort_keys=True) + '\n' \
                    + "And you are equipped with:\n" + json.dumps(equips, sort_keys=True) + '\n' \
                    + "And your backpack has:\n" + json.dumps(backpack, sort_keys=True) + '\n' \
                    + self.check_status()
        else:
            item_name = block.get('params')['item_name']
            quantity_itemslots = 0
            for item in self.shared_perception_dict["Possessions"]["ItemSlots"]:
                if item and item["Prefab"] == item_name:
                    quantity_itemslots += item.get("Quantity", 0)
            quantity_equipslots = 0
            for item in self.shared_perception_dict["Possessions"]["EquipSlots"]:
                if item and item["Prefab"] == item_name:
                    quantity_equipslots += item.get("Quantity", 0)
            quantity_backpack = 0
            for item in self.shared_perception_dict["Possessions"]["Backpack"]:
                if item and item["Prefab"] == item_name:
                    quantity_backpack += item.get("Quantity", 0)
            
            itemslots_response = "Your have {} {} in your ItemSlots.\n".format(quantity_itemslots, item_name, ) if quantity_itemslots > 0 else ""
            equipslots_response = "Your have {} {} in your EquipSlots.\n".format(quantity_equipslots, item_name, ) if quantity_equipslots > 0 else ""
            backpack_response = "Your have {} {} in your Backpack.\n".format(quantity_backpack, item_name, ) if quantity_backpack > 0 else ""
            return itemslots_response + equipslots_response + backpack_response + self.check_status()

    def check_status(self):
        return "Your current status is: " \
                + "Health: " + self.shared_perception_dict["RoleStatus"]["Health"] + ', ' \
                + "Sanity: " + self.shared_perception_dict["RoleStatus"]["Sanity"] + ', ' \
                + "Hunger: " + self.shared_perception_dict["RoleStatus"]["Hunger"] + ', ' \
                + "Moisture: " + self.shared_perception_dict["RoleStatus"]["Moisture"] + ', ' \
                + "Temperature: " + self.shared_perception_dict["RoleStatus"]["Temperature"]