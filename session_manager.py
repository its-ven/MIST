import json
from api import tokenize
from utils import log, LogType, read_from_folder

def load_history(persona_path: str, ctx_size: int):
    try:
        cycle_files = read_from_folder(f"{persona_path}/cycles", ".json")
        cycles = []
        for cycle in cycle_files:
            with open(cycle, "r", encoding="utf-8") as file:
                cycle_files.append(json.load(file))
        cycles.reverse()
        total_tokens = 0
        limit_reached = False
        summaries = []
        for cycle in cycles:
            if not limit_reached:
                total_tokens += tokenize(str(cycle), True)
            if total_tokens > ctx_size:
                log(LogType.system, f"[Session] Loading history ({total_tokens}/{ctx_size})", updatable_str=True)
                cycles.append(cycle)
            else:
                limit_reached == True
                summaries.append(cycle["cognitive_response"]["cycle_summary"])
        cycles.reverse()
        summaries.reverse()
        return cycles, summaries
    except Exception as e:
        raise e

def save_history(persona_path: str, history:list):
    with open(f"{persona_path}/history.json", "w", encoding="utf-8") as file:
        file.write(json.dumps({"session": history}, indent=4, ensure_ascii=False))

def save_cycle(checkpoint_file: str, cycle: dict):
    with open(checkpoint_file, "w", encoding="utf-8") as file:
        file.write(json.dumps(cycle, indent=4, ensure_ascii=False))