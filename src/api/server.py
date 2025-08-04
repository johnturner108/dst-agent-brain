from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import logging
import json
import re
from ..tools.parse_tool import parse_assistant_message
from ..core.task import Task
from ..config.prompt import systemPrompt
from ..tools.tool_executor import parse_action_str
from ..utils.queues import ActionQueue, DialogQueue
from ..config.settings import settings

app = FastAPI()

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)

# --- 全局状态对象 ---
action_queue = ActionQueue(maxsize=settings.ACTION_QUEUE_SIZE)
dialog_queue = DialogQueue(maxsize=settings.DIALOG_QUEUE_SIZE)
current_perception: Dict = {}
self_uid = 0
task_instance = Task(action_queue, current_perception, dialog_queue, self_uid)

# action_queue.put_action(parse_action_str("Action(PATHFIND, -, 400, 350, -) = -"))
# action_queue.put_action(parse_action_str("Action(STOP, -, -, -, -) = -"))
# action_queue.put_action(parse_action_str("Action(BUILD, -, 262, 100, homesign) = -"))
# action_queue.put_action(parse_action_str("Action(CHOP, -, -, -, -) = 118707"))


@app.get("/{guid}/decide/{layer}")
async def decide(guid: str, layer: str):
    global self_uid
    self_uid = guid
    if layer == "Behaviour":
        response_data = action_queue.get_action()
        return JSONResponse(content=response_data)
    elif layer == "Dialog":
        response_data = {"Type": "Speak", "Utterance": dialog_queue.get_dialog()}
        return JSONResponse(content=response_data)
    else:
        raise HTTPException(status_code=404, detail="Layer not found")


@app.get("/stats")
async def stats():
    return JSONResponse(content=action_queue.get_stats())


@app.get("/inference-status")
async def inference_status():
    status = {
        "inference_running": task_instance.is_inference_running(),
        "abort_event_set": task_instance.abort_event.is_set()
    }
    return JSONResponse(content=status)


@app.get("/abort-inference")
async def abort_inference():
    aborted = task_instance.abort_current_inference()
    return JSONResponse(content={"aborted": aborted})


@app.get("/vision")
async def get_vision():
    return JSONResponse(content=current_perception)


@app.post("/{guid}/perceptions")
async def receive_perception(guid: str, request: Request):
    global self_uid
    self_uid = guid
    data = await request.json()
    current_perception.clear()
    current_perception.update(data)
    # # 提取current_perception中的"Recipes"字段并保存为json文件
    # recipes = current_perception.get("Recipes", [])
    # # 直接保存原始recipes到文件
    # with open("recipes.json", "w", encoding="utf-8") as f:
    #     json.dump(recipes, f, indent=4, ensure_ascii=False)


    return JSONResponse(content={"status": f"Perception for GUID {guid} received and is being processed."}, status_code=202)


@app.post("/{guid}/events")
async def receive_event(guid: str, request: Request):
    data = await request.json()
    print(data)
    if "BUILD" in data.get("Name"):
        if data.get("Type") == "Action-Failed":
            
            info = "Info: {}".format(data.get("Info")) if data.get("Info") else ""
            print(info)
            task_instance.processStream("The action {} -> {} failed. {}".format(data.get("Name"), data.get("Value"), info))
    elif data.get("Name") == "PATHFIND":
        if data.get("Type") in "Action-End":
            task_instance.processStream("You've arrived at " + str(data.get("Value")))
        else:
            task_instance.processStream("Can't find way to " + str(data.get("Value")) + "or is interuppted")
    else:
        if data.get("Type") in "Action-End":
            task_instance.processStream("The action {} -> {} done.".format(data.get("Name"), data.get("Value")))
        elif data.get("Type") == "Action-Failed":
            task_instance.processStream("The action {} -> {} failed.".format(data.get("Name"), data.get("Value")))
    # logging.info(f"Event received for GUID {guid}: {data}")
    return JSONResponse(content={"status": "received event"})


@app.post("/{guid}/command")
async def receive_command(guid: str, request: Request):
    data = await request.json()
    command = data.get("command", "")
    try:
        surroundings = task_instance.toolExecutor.executeTool(parse_assistant_message("<check_surroundings></check_surroundings>")[0])
        available_positions = "The positions that you can go to: " + json.dumps(current_perception["Positions"], sort_keys=True)
        stream_input = f"The current entities are surrounding you:\n{surroundings}\n\n{available_positions}\n\n{command}"
        dialog_queue.put_dialog("Task Start: "+ command)

        task_instance.processStream(stream_input)
    except Exception as e:
        logging.error(f"Error while processing command: {e}")
        raise HTTPException(status_code=500, detail="Failed to process command")

    return JSONResponse(content={"status": f"Command for GUID {guid} received and is being processed."}, status_code=202)


if __name__ == "__main__":
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8081, reload=True) 