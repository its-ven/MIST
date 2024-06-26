from functions import register
from utils import log, LogType
from core import Session
import time
import re
import random

@register("Send a message to the user. If `rhetorical` bool is True, the user won't be asked for a response")
def chat(message: str, rhetorical: bool = False):
    pattern = r'(?<=[!.?])\s+(?=[A-Z])|(?<=\n)'
    messages = re.split(pattern, message)
    messages = [entry.strip() for entry in messages if entry.strip()]
    for entry in messages:
        log(LogType.response, entry, with_prefix=False)
        time.sleep(1)
        
    if not rhetorical:
        response = input("> ")
        Session.add_event("User", response)

@register(f"Probe your memory database for experiences, information, or events.")
def recall(questions: list[str]):
    memories = Session.memory.query(questions)
    return memories

@register("Saves your current activity and temporarily shuts you down")
def shutdown():
    return Session.quit()

@register("Go idle and wait until the user stops being AFK")
def go_idle():
    log(LogType.action, "Going idle. Enter message to resume session.")
    response = input("> ")
    Session.add_event("User", response)
    return "User has returned"