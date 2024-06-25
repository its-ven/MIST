import json
from api import tokenize
from server import instance
from utils import log, LogType

def load_history(persona_path: str, ctx_size: int):
    with open(f"{persona_path}/history.json", "r", encoding="utf-8") as file:
        history = list(json.load(file)).reverse()
    loaded_cycles = []
    older_cycles = []
    total_tokens = 0
    limit_reached = False
    for cycle in history:
        if not limit_reached:
            total_tokens += tokenize(str(cycle), True)
        if total_tokens > ctx_size:
            log(LogType.system, f"[Session] Loading history ({total_tokens}/{ctx_size})", updatable_str=True)
            loaded_cycles.append(cycle)
        else:
            limit_reached == True
            older_cycles.append(cycle["cognitive_response"]["summary"])
    loaded_cycles.reverse()
    older_cycles.reverse()
    return loaded_cycles, older_cycles

def save_history(persona_path: str, history:list):
    with open(f"{persona_path}/history.json", "w", encoding="utf-8") as file:
        file.write(json.dumps({"session": history}, indent=4, ensure_ascii=False))

def save_cycle(checkpoint_file: str, cycle: dict):
    with open(checkpoint_file, "w", encoding="utf-8") as file:
        file.write(json.dumps(cycle, indent=4, ensure_ascii=False))