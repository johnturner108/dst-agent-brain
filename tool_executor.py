import re
import json

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
    action_obj = {
        "Type": "Action",
        "Action": action_type,
        "InvObject": inv_object,
        "Recipe": recipe,
        "Name": action_str, # 使用完整的动作字符串作为 Name
        "PosX": posX,
        "Target": target,
        "PosZ": posZ,
        "WFN": action_str # 使用完整的动作字符串作为 WFN
    }
    return action_obj
    

class ToolExecutor:
    """
    ToolExecutor 类负责根据大型语言模型 (LLM) 返回的工具使用指令，
    更新应用程序的全局状态（即 current_action 字典）。
    """
    def __init__(self, action_queue, shared_perception_dict):

        self.action_queue = action_queue
        self.shared_perception_dict = shared_perception_dict
        self.map = {}
        print(f"ToolExecutor 初始化，动作队列: {self.action_queue} 和 感知字典：{self.shared_perception_dict}")
        

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
                    self.map[loc_name] = block.get('params')['coords']
                    return "The location {} has been marked".format(loc_name)
                elif action_name == 'check_map':
                    return "The map has the following locations:\n" + json.dumps(self.map, sort_keys=True)

        print("在内容块中未找到 'perform_action' 工具使用指令。")
    
    def execute_perform_action(self, block):

        params = block.get('params', {}) # 获取工具指令的参数
        if "\n" in params.get('action'):
            action_strs = params.get('action').split("\n")
            for action_str in action_strs:
                action_obj = parse_action_str(action_str)
                if action_obj is str:
                    return action_obj
                self.action_queue.put_action(action_obj)
        else:
            action_str = params.get('action') # 例如：'Action(BUILD, -, -, -, axe)'
            action_obj = parse_action_str(action_str)
            if action_obj is str:
                return action_obj
            self.action_queue.put_action(action_obj)
        # requires_approval = params.get('requires_approval') # 这个参数当前未在 current_action 中使用
        return # 执行第一个工具使用块后即返回，因为用户要求“中止”
    
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