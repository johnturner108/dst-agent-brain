import re
from typing import List, Dict, Any, Tuple

ALLOWED_TOOLS = {"check_inventory", "perform_action", "check_surroundings", "task_completion", "check_equipslots", "mark_loc", "check_map"}  # 只允许的工具标签名

def parse_assistant_message(assistant_message: str) -> Tuple[List[Dict[str, Any]], bool]:
    content_blocks = []
    last_index = 0

    tool_pattern = re.compile(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)
    param_pattern = re.compile(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)

    for match in tool_pattern.finditer(assistant_message):
        start, end = match.span()

        # 处理工具调用之前的文本
        if start > last_index:
            text_content = assistant_message[last_index:start].strip()
            if text_content:
                content_blocks.append({"type": "text", "content": text_content})

        tool_name = match.group(1)
        tool_content = match.group(2)

        if tool_name in ALLOWED_TOOLS:
            # 是合法的工具调用，解析参数
            params = {}
            for param_match in param_pattern.finditer(tool_content):
                param_name = param_match.group(1)
                param_value = param_match.group(2).strip()
                params[param_name] = param_value

            content_blocks.append({
                "type": "tool_use",
                "name": tool_name,
                "params": params
            })
        else:
            # 不是合法工具，原样保留为文本
            content_blocks.append({
                "type": "text",
                "content": assistant_message[start:end].strip()
            })

        last_index = end

    # 处理结尾剩余文本
    if last_index < len(assistant_message):
        remaining_text = assistant_message[last_index:].strip()
        if remaining_text:
            content_blocks.append({"type": "text", "content": remaining_text})

    has_tool_use = any(block["type"] == "tool_use" for block in content_blocks)
    return content_blocks, has_tool_use


# --- Example Usage ---
message = """
<check_map>
<name>Pig houses</name>
</check_map>"""

content_blocks = parse_assistant_message(message)
print(content_blocks)