import json
import re

def merge_recipe():
    # 读取英文菜谱文件
    with open("recipes_en.json", "r", encoding="utf-8") as f:
        recipes_en = json.load(f)

    # 读取中文菜谱文件
    with open("recipes_zh.json", "r", encoding="utf-8") as f:
        recipes_zh = json.load(f)

    # 创建中文菜谱的映射字典，以name为键
    zh_recipes_map = {}
    for recipe in recipes_zh:
        zh_recipes_map[recipe["name"]] = recipe


    # 打印菜谱长度
    print(len(recipes_en))
    print(len(recipes_zh))

    # 合并菜谱，为每个英文菜谱添加中文显示名称
    merged_recipes = []
    for en_recipe in recipes_en:
        # 复制英文菜谱
        merged_recipe = en_recipe.copy()
        
        # 添加英文显示名称
        merged_recipe["display_name_en"] = en_recipe["display_name"]
        
        # 查找对应的中文菜谱
        if en_recipe["name"] in zh_recipes_map:
            zh_recipe = zh_recipes_map[en_recipe["name"]]
            merged_recipe["display_name_zh"] = zh_recipe["display_name"]
            
            # 同时更新原料的中文显示名称
            if "ingredients" in merged_recipe and "ingredients" in zh_recipe:
                for i, en_ingredient in enumerate(merged_recipe["ingredients"]):
                    for zh_ingredient in zh_recipe["ingredients"]:
                        if en_ingredient["type"] == zh_ingredient["type"]:
                            merged_recipe["ingredients"][i]["display_name_zh"] = zh_ingredient["display_name"]
                            break
        else:
            # 如果没有找到对应的中文菜谱，使用英文名称
            merged_recipe["display_name_zh"] = en_recipe["display_name"]
        
        merged_recipes.append(merged_recipe)

    # 保存合并后的菜谱到新文件
    with open("recipes_merged.json", "w", encoding="utf-8") as f:
        json.dump(merged_recipes, f, ensure_ascii=False, indent=4)

    print(f"成功合并了 {len(merged_recipes)} 个菜谱")
    print("合并后的文件已保存为 recipes_merged.json")

def process_recipe():
    with open("recipes_merged.json", "r", encoding="utf-8") as f:
        recipes = json.load(f)

    new_recipes = []
    for recipe in recipes:
        # 去除掉level字段中为0的
        level = recipe.get("level")
        new_level = {}
        for key, value in level.items():
            if value != 0:
                new_level[key] = value
        recipe["level"] = new_level
        new_recipes.append(recipe)

    with open("recipes_merged_processed.json", "w", encoding="utf-8") as f:
        json.dump(new_recipes, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    # merge_recipe()
    process_recipe()












# "level": {
#     "PERDOFFERING": 0,
#     "WANDERINGTRADERSHOP": 0,
#     "FOODPROCESSING": 0,
#     "ANCIENT": 2,
#     "CARTOGRAPHY": 0,
#     "SCIENCE": 0,
#     "SEAFARING": 0,
#     "CARNIVAL_HOSTSHOP": 0,
#     "SPIDERCRAFT": 0,
#     "CARRATOFFERING": 0,
#     "SHADOW": 0,
#     "MAGIC": 0,
#     "SCULPTING": 0,
#     "WAGPUNK_WORKSTATION": 0,
#     "LUNARFORGING": 0,
#     "RABBITKINGSHOP": 0,
#     "FISHING": 0,
#     "WARGOFFERING": 0,
#     "WORMOFFERING": 0,
#     "DRAGONOFFERING": 0,
#     "HERMITCRABSHOP": 0,
#     "CARPENTRY": 0,
#     "MADSCIENCE": 0,
#     "CARNIVAL_PRIZESHOP": 0,
#     "RABBITOFFERING": 0,
#     "SHADOWFORGING": 0,
#     "BOOKCRAFT": 0,
#     "ROBOTMODULECRAFT": 0,
#     "MOON_ALTAR": 0,
#     "CELESTIAL": 0,
#     "ORPHANAGE": 0,
#     "TURFCRAFTING": 0,
#     "WINTERSFEASTCOOKING": 0,
#     "PIGOFFERING": 0,
#     "MASHTURFCRAFTING": 0,
#     "BEEFOFFERING": 0,
#     "CATCOONOFFERING": 0
# },