import server
from core import Session
from functions import Toolkit
from persona import Persona
import traceback
from utils import log, LogType, _boot_padding, _shuffle_acronym
from settings import llama_update, disable_splash
import sys
if __name__ == "__main__":
    try:
        if not disable_splash:
            log(LogType.boot_sequence,"     __    __     __     ______     ______        ", is_stream=False)
            log(LogType.boot_sequence,"    /\ \"-./  \   /\ \   /\  ___\   /\__  _\\       ", is_stream=False)
            log(LogType.boot_sequence,"    \ \ \-./\ \  \ \ \  \ \___  \  \/_/\ \/       ", is_stream=False)
            log(LogType.boot_sequence,"     \ \_\ \ \_\  \ \_\  \/\_____\    \ \_\\       ", is_stream=False)
            log(LogType.boot_sequence,"      \/_/  \/_/   \/_/   \/_____/     \/_/       ", is_stream=False)
            log(LogType.boot_sequence,"                                                  ", is_stream=False)
            log(LogType.boot_sequence, _boot_padding(_shuffle_acronym()), is_stream=False)
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
        session.parse(tweak_response=True)
    except SystemExit:
        pass
    except:
        tb = traceback.format_exc()
        log(LogType.error, tb)
    finally:
        server.close()