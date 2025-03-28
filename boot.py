import server
from core import Session
from functions import Toolkit
from persona import Persona
import traceback
from utils import log, LogType, _boot_padding, _shuffle_acronym
from settings import llama_update, disable_splash, override_responses
import sys
if __name__ == "__main__":
    try:
        if not disable_splash:
            log(LogType.boot_sequence,"     __    __     __     ______     ______        ")
            log(LogType.boot_sequence,"    /\ \"-./  \   /\ \   /\  ___\   /\__  _\\       ")
            log(LogType.boot_sequence,"    \ \ \-./\ \  \ \ \  \ \___  \  \/_/\ \/       ")
            log(LogType.boot_sequence,"     \ \_\ \ \_\  \ \_\  \/\_____\    \ \_\\       ")
            log(LogType.boot_sequence,"      \/_/  \/_/   \/_/   \/_____/     \/_/       ")
            log(LogType.boot_sequence,"                                                  ")
            log(LogType.boot_sequence, _boot_padding(_shuffle_acronym()))
            log(LogType.boot_sequence, _boot_padding(""))
        if llama_update():
            server.update()
        # Load a persona. Defaults to `DEFAULT_PERSONA` in `.env`
        persona = Persona()
        # Create toolkit with all registered functions
        toolkit = Toolkit()
        # Start persona session, extend toolkit with core funcs.
        session = Session(persona=persona, toolkit=toolkit)
        # Init
        session.add_event("Self", f"Boot sequence complete! Last boot date: {persona.config['last_boot']}.")
        persona.set_last_boot()
        session.parse(override_responses=override_responses)
    except SystemExit:
        pass
    except:
        tb = traceback.format_exc()
        log(LogType.error, tb)
    finally:
        server.close()