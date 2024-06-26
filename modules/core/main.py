from functions import register
from utils import log, LogType
from core import Session
import time
import re
import random

@register("If `rhetorical` is True, sends a one-way message to the user. Otherwise, prompts user for a response")
def chat(message: str, rhetorical: bool = False):
    pattern = r'(?<=[!.?])\s+(?=[A-Z])|(?<=\n)|(?<=\\n)'
    messages = re.split(pattern, message)
    messages = [entry.strip() for entry in messages if entry.strip()]
    for entry in messages:
        log(LogType.response, entry.replace("\\n", ""), with_prefix=False, str_as_stream=True)
        if messages[-1] != entry: 
            time.sleep(1.3)
        
    if not rhetorical:
        response = input("> ")
        Session.add_event("User", response)

@register(f"Probe your memory database for experiences, information, or events")
def recall(questions: list[str]):
    memories = Session.memory.query(questions)
    return memories

@register("Saves your current activity and temporarily shuts you down")
def shutdown():
    return Session.quit()

@register("Go idle if the user is AFK or there is nothing to do")
def go_idle():
    log(LogType.action, "Going idle. Enter message to resume session.")
    response = input("> ")
    Session.add_event("User", response)
    return "User has returned"