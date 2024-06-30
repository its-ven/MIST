from functions import register
from utils import log, LogType
from core import Session
import time
import re
import random
from typing import Literal

@register("If `is_rhetorical` is True, sends a one-way message to the user. Otherwise, prompts user for a response")
def chat(message: str, is_rhetorical: bool = False):
    pattern = r'(?<=[!.?])\s+(?=[A-Z])|(?<=\n)|(?<=\\n)'
    messages = re.split(pattern, message)
    messages = [entry.strip() for entry in messages if entry.strip()]
    for entry in messages:
        log(LogType.response, entry.replace("\\n", ""), with_prefix=False, str_as_stream=True)
        if messages[-1] != entry: 
            time.sleep(1.3)
        
    if not is_rhetorical:
        response = input("> ")
        Session.add_event("User", response)

@register("Searches your memories of a memory_type")
def search_memories(queries: list[str], memory_type: Literal["user", "self", "world_knowledge"]):
    memories = Session.internal_memory.query(queries, memory_type.lower())
    return memories

@register("Store information for a given memory_type")
def store_memories(memory_type: Literal["user", "self", "world_knowledge"], memories: list[str]):
    Session.internal_memory.add(memories, memory_type)
    return f"Upserted memories for '{memory_type}'."

@register("Saves your current activity and temporarily shuts you down")
def shutdown():
    return Session.quit()

@register("Makes you go idle if the user goes AFK or there is nothing to do")
def go_idle():
    log(LogType.action, "Going idle. Enter message to resume session.")
    response = input("> ")
    Session.add_event("User", response)
    return "User has returned"