import json
import os
from utils import log, LogType, capfirst, get_dir, Time
import settings

CONFIG = {
    "last_boot": "Never. This is my first boot"
}

class Persona:
    def __init__(self, persona:str = settings.default_persona):
        """
        Load a persona. Defaults to `DEFAULT_PERSONA` in `.env`
        """
        self.path = get_dir(f"personas/{persona}")
        with open(os.path.join(self.path, "persona.json"), "r", encoding="utf-8") as file:
            persona_file = json.load(file)

        self.profile = {}
        self.weighables = False
        self.subjectives = False
        
        for k, v in persona_file.items():
            match k.casefold():
                case "name":
                    self.profile["name"] = str(v)
                case "description":
                    self.profile["description"] = str(v)
                case "character":
                    self.profile["character"] = dict(v)
                    self.weighables = True
                    self.subjectives = True
                case "interests_and_biases":
                    self.profile["interests_and_biases"] = dict(v)
                    self.weighables = True
                    self.subjectives = True
                case "fears":
                    self.profile["fears"] = list(v)
                    self.subjectives = True
                case "aspirations":
                    self.profile["aspirations"] = list(v)
                    self.subjectives = True
                case "thinking_process":
                    self.profile["thinking_process"] = str(v)
                case "conversation_style":
                    self.profile["conversation_style"] = str(v)
                case "rules":
                    self.profile["rules"] = list(v)
                case "priming":
                    self.profile["priming"] = v
        
        if not os.path.isfile(os.path.join(self.path, "config.json")):
            with open(os.path.join(self.path, "config.json"), "w", encoding="utf-8") as file:
                file.write(json.dumps(CONFIG, indent=4, ensure_ascii=False))
        
        with open(os.path.join(self.path, "config.json"), "r", encoding="utf-8") as file:
            config = json.load(file)
            self.config = config

    def get_profile(self, value:str = None):
        """
        Return the full profile prompt or just the given raw value.
        """
        try:
            if value:
                try:
                    val = self.profile[value.casefold()]
                    return val
                except:
                    log(LogType.warning, f"[Persona] Value '{value}' not found!")
                    return None

            else:
                if self.profile == {}:
                    raise log(LogType.error, "[Persona] Persona was not initialized!")
                else:
                    profile = []

                    profile.append(f"Name:\n{self.profile['name']}")
                    profile.append(f"Bio:\n{self.profile['description']}")
                    
                    if "fears" in self.profile:
                        profile.append("Fears:\n" + "\n".join([f"- {capfirst(fear)}" for fear in self.profile["fears"]]))
                        
                    if "aspirations" in self.profile:
                        profile.append("Aspirations:\n" + "\n".join([f"- {capfirst(aspiration)}" for aspiration in self.profile["aspirations"]]))
                    
                    if "thinking_process" in self.profile:
                        profile.append(f"Thinking Process: {self.profile['thinking_process']}")
                    
                    if "conversation_style" in self.profile:
                        profile.append(f"Conversation Style: {self.profile['conversation_style']}")
                    
                    if "rules" in self.profile:
                        profile.append("Rules:\n" + "\n".join([f"- {rule}" for rule in self.profile["rules"]]))
                        
                    if self.weighables:
                        profile.append(f"Stated below are your biases, ranging between `-100` and `100` .\nThe more positive the bias, the more you lean towards it.\n`0` is neutral.")
                    
                        if "character" in self.profile:
                            profile.append("Personality traits:\n" + "\n".join([f"- {capfirst(key)}: `{value}`" for key, value in self.profile["character"].items()]))

                        if "interests_and_biases" in self.profile:
                            profile.append("Interests and Biases:\n" + "\n".join([f"- {capfirst(key)}: `{value}`" for key, value in self.profile["interests_and_biases"].items()]))

                    return "\n\n".join(profile)
        except:
            raise log(LogType.error, "[Persona] Persona template is malformed!")
    
    def set_last_boot(self):
        self.config["last_boot"] = Time.full()
        with open(os.path.join(self.path, "config.json"), "w", encoding="utf-8") as file:
            file.write(json.dumps(self.config, indent=4, ensure_ascii=False))