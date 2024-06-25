from functions import register
from utils import log, LogType
from core import Session

@register("Send a message to the user. If `rhetorical` bool is True, the user won't be asked for a response")
def chat(message: str, rhetorical: bool = False):
    log(LogType.response, message, with_prefix=False)
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