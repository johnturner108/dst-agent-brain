from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import logging
import json
import re
from parse_tool import parse_assistant_message
from task import Task
from prompt import systemPrompt
from tool_executor import parse_action_str
from utils import ActionQueue, DialogQueue

app = FastAPI()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 全局状态对象 ---
action_queue = ActionQueue(maxsize=20)
dialog_queue = DialogQueue(maxsize=20)
current_perception: Dict = {}
task_instance = Task(action_queue, current_perception, dialog_queue)


@app.get("/{guid}/decide/{layer}")
async def decide(guid: str, layer: str):
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
    data = await request.json()
    current_perception.clear()
    current_perception.update(data)
    return JSONResponse(content={"status": f"Perception for GUID {guid} received and is being processed."}, status_code=202)


@app.post("/{guid}/events")
async def receive_event(guid: str, request: Request):
    data = await request.json()
    if data.get("Type") in ("Action-End", "Action-Failed"):
        task_instance.processStream(json.dumps(data))
    # logging.info(f"Event received for GUID {guid}: {data}")
    return JSONResponse(content={"status": "received event"})


@app.post("/{guid}/command")
async def receive_command(guid: str, request: Request):
    data = await request.json()
    command = data.get("command", "")
    try:
        surroundings = task_instance.toolExecutor.executeTool(parse_assistant_message("<check_surroundings></check_surroundings>")[0])
        stream_input = f"The current entities are surrounding you:\n{surroundings}\n\n{command}"
        task_instance.processStream(stream_input)
    except Exception as e:
        logging.error(f"Error while processing command: {e}")
        raise HTTPException(status_code=500, detail="Failed to process command")

    return JSONResponse(content={"status": f"Command for GUID {guid} received and is being processed."}, status_code=202)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8081, reload=True)
