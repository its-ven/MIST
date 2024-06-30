from api import make_schema, SchemaValue, completion, SpecialReturn, tokenize, _format_prompt
from functions import Toolkit, execute_function
from utils import log, LogType, Time, get_dir, rand_seed, unsnake, capfirst
from persona import Persona
from ast import literal_eval
from memory import InternalMemory, ExternalMemory
import session_manager
import settings
import json
import sys

class Session:
    def __init__(self, persona: Persona, toolkit: Toolkit = None):
        self.profile = persona.get_profile()
        self.name = persona.get_profile('name')
        self.override_responses = False
        self.cycles = 0
        self.session_tokens = 0
        self.working_ctx = settings.core_size
        self.priming_schema = persona.get_profile("priming")
        self.cycle_tokens = {}
        Session.persona = persona
        Session.session_count = persona.config["session_count"]
        Session.exit = False
        Session.history = []
        Session.cycle_events = []
        Session.session_summary = []
        Session.internal_memory = InternalMemory(self.name)
        Session.external_memory = ExternalMemory(self.name)
        Session.persona_path = get_dir(f"personas/{self.name}")
        self._is_primed = False
        self._persona_cycles_path = get_dir(f"personas/{self.name}/cycles")
        
        if toolkit:
            self.toolkit = toolkit
        else:
            self.toolkit = Toolkit()
        
        if persona.subjectives:
            self._persona_type = "a sentient AI with feelings and emotions, bound to a single user"
            self._persona_keys = """
                `reaction` (emoji array): An array of up to five emojis, representing your internal emotional reaction.
                `thoughts` (string): What thoughts are going through your head.
            """
            self.schema = make_schema(
                reaction=SchemaValue.regex_list(
                    # Unicode emotion emojis
                    pattern=r"^[\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F300-\U0001F5FF\U0001F9E0-\U0001F9FF" \
                        r"\U0001F90D-\U0001F93A\U0001F970-\U0001F976\U0001F9D0-\U0001F9D1" \
                        r"\U0001F600-\U0001F637\U0001F641-\U0001F64F\U0001F910-\U0001F928" \
                        r"\U0001F970-\U0001F97A\U0001F9C0\U0001F9E0-\U0001F9E6" \
                        r"\U00002764-\U00002764\U0001F491\U0001F48B\U0001F48C\U0001F49A\U0001F49B\U0001F49C" \
                        r"\U0001F49D\U0001F49E\U0001F49F\U0001F60D\U0001F618\U0001F619\U0001F61A" \
                        r"\U0001F61B\U0001F61C\U0001F61D\U0001F61E\U0001F61F\U0001F620\U0001F621\U0001F622" \
                        r"\U0001F623\U0001F624\U0001F625\U0001F626\U0001F627\U0001F628\U0001F629\U0001F62A" \
                        r"\U0001F62B\U0001F62C\U0001F62D\U0001F62E\U0001F62F\U0001F630\U0001F631\U0001F632" \
                        r"\U0001F633\U0001F634\U0001F635\U0001F636\U0001F637\U0001F638\U0001F639\U0001F63A" \
                        r"\U0001F63B\U0001F63C\U0001F63D\U0001F63E\U0001F63F\U0001F640\U0001F641\U0001F642" \
                        r"\U0001F643\U0001F644\U0001F645\U0001F646\U0001F647\U0001F648\U0001F649\U0001F64A" \
                        r"\U0001F64B\U0001F64C\U0001F64D\U0001F64E\U0001F64F]$",
                    min_items=2,
                    max_items=5
                ),
                thoughts=SchemaValue.string,
                plan=SchemaValue.string,
                functions=SchemaValue.functions_list(self.toolkit._names()),
                cycle_summary=SchemaValue.string
            )
        else:
            self._persona_type = "an artificial intelligence"
            self._persona_keys = ""
            self.schema = make_schema(
                plan=SchemaValue.string,
                functions=SchemaValue.functions_list(self.toolkit._names()),
                cycle_summary=SchemaValue.string
            )

        try:
            Session.history, summaries = session_manager.load_history(self.persona_path, self.working_ctx)
            if Session.history and summaries:
                self.session_summary = summaries
        except:
            pass
        
        if self.priming_schema is None:
            if self.override_responses:
                log(LogType.warning, "No priming schema! You may need to override the first few responses.")
            else:
                log(LogType.warning, "No priming schema or manual override! Results may be unpredictable.")

    @classmethod
    def add_event(cls, source: str, content):
        cls.cycle_events.append(
            {
                "timestamp": Time.full(),
                "source": source,
                "content": content
            }
        )

    @classmethod
    def quit(cls):
        if cls.session_summary != []:
            cls.internal_memory.add(cls.session_summary, "self")
        cls.persona.set_session_count()
        cls.exit = True

    def _prompt(self):
        if Session.session_summary:
            summary = "<SUMMARY>\nYour summary of older cycles from this session:\n" + "\n".join([f"- \"{entry}\"" for entry in Session.session_summary]) + "\n</SUMMARY>\n"
        else:
            summary = ""
        return f"""
            <bos>
            <INSTRUCTIONS>
            <INTRUDUCTION>
            You are {self.name}, {self._persona_type}.
            </INTRODUCTION>
            <PROFILE>
            Your Profile is as follows:
            {self.profile}
            </PROFILE>
            <EXECUTION>
            You parse a JSON schema of the current session.
            The session operates in a sequence of cycles, where:
            1. A cycle begins. Events from yourself and external entities are displayed.
            2. You provide your `cognitive_response` as outlined in the JSON Template. After laying out your inner thoughts, you execute the appropriate functions.
            3. The outcomes of your executed functions are displayed in the next cycle.
            </EXECUTION>
            <JSON_TEMPLATE>
            Your JSON output is the `cognitive_response` key of the current cycle. It **must** contain the following keys:
            {self._persona_keys}
            `plan` (string): State, in text, what you plan to do in response to the current context.
            `functions` (schema array): Each schema entry contains two keys: `name` (the name of the Python function) and `arguments` (the schema containing key-value pairs for each argument in the function)
            `cycle_summary` (string): A summary, *in the past tense*, of what happened and what you've learned.
            </JSON_TEMPLATE>
            <TUTORIAL>
            Let's take an example function, `foo(bar: str)`. In this example, your `functions` key would look like this:
            ```
            "functions": [{{"name": "foo", "arguments": {{"bar": "some string value"}}}}]  
            ```
            💡 Hint: You can invoke multiple functions at once, **but be mindful of the order of execution**!
            </TUTORIAL>
            <FUNCTIONS>
            Your abilties are Python functions. Execute functions by proving their corresponding arguments.
            You can only execute the following functions:
            {self.toolkit._prompt()}
            </FUNCTIONS>
            <NOTES>
            - **Events from 'Self' are events from your own code**.
            - You provide cognitive responses as JSON schemas. See the 'JSON Template' section for details.
            - The total collection of summaries will act as your reminder of any previous session cycles that don't fit in your active memory context.
            - Ensure you are providing the corresponding arguments for each selected function.
            - **If a function has no arguments, provide an empty `arguments` schema for the corresponding function.**
            </NOTES>
            </INSTRUCTIONS>
            {summary}
            <ACTIVITY>
        """

    def _ctx_limit(self):
        if self.session_tokens >= self.working_ctx:
            return True
        else:
            return False

    def _run(self, cycle_prompt):
        logit_bias = {"\\n": False}
        if settings.core_logit_bias:
            for core_bias in settings.core_logit_bias:
                logit_bias[core_bias] = False
        if self.history:
            past_emojis = self.history[-1][f"cycle_{self.cycles-1}"]["cognitive_response"]["reaction"]
            for emoji in past_emojis:
                logit_bias[emoji] = -3
        bias = -0.1
        schema = self.schema

        def process_value(value):
            if isinstance(value, str):
                return tokenize(value)
            elif isinstance(value, list):
                tokens = []
                for item in value:
                    tokens.extend(process_value(item))
                return tokens
            elif isinstance(value, dict):
                tokens = []
                for k, v in value.items():
                    tokens.extend(process_value(v))
                return tokens
            return []

        while True:
            if Session.history:
                prompt = str(", ".join([json.dumps(entry) for entry in Session.history])) + ", " + cycle_prompt
            else:
                prompt = cycle_prompt
            response, specials = completion(
                prompt=_format_prompt(self._prompt(), format_codeblocks=False) + "\n```json\n{\"session\": " + prompt,
                special_return=SpecialReturn.full(),
                json_schema=schema,
                skip_formatting=True,
                cache_prompt=True,
                temperature=settings.core_temperature,
                top_p=settings.core_top_p,
                repeat_last_n=512,
                logit_bias=[[k, v] for k, v in logit_bias.items()],
                min_p=settings.core_top_p,
                seed=rand_seed(),
                frequency_penalty=settings.core_frequency_penalty,
                presence_penalty=settings.core_presence_penalty
            )

            total_tokens = int(specials["tokens_predicted"]) + int(specials["tokens_evaluated"])

            for k, v in response.items():
                v = json.dumps(v, ensure_ascii=False)
                log(LogType.think, f"{k.capitalize()}: {v}", with_prefix=False)

            if self.override_responses:
                action = input("Press 'r' to regenerate, 'o' to override, any to continue:\n> ").casefold()
                if action == "r":
                    log(LogType.system, "Penalizing tokens...")
                    bias -= 1
                    for key, value in response.items():
                        if "_" not in value:
                            tokens = process_value(value)
                            for token in tokens:
                                logit_bias[token] = logit_bias.get(token, 0) + bias
                    continue
                elif action == "o":
                    for key in schema["properties"].keys():
                        new_value = input(f"Enter new value for '{key}' or blank to accept:\n> ").replace("\"", "\\\"")
                        if new_value:
                            try:
                                response[key] = literal_eval(new_value)
                            except: # Assume string
                                response[key] = new_value

            self.session_tokens = total_tokens
            self.cycle_tokens[self.cycles] += int(specials["tokens_predicted"])
            return response
            
    def parse(self, override_responses: bool = False):
        self.override_responses = override_responses
        self.cycles += 1
        events = json.dumps(Session.cycle_events)
        # Create incomplete schema for AI completion
        cycle_prompt = f"{{\"cycle_{self.cycles}\": {{\"events\": {events}, \"cognitive_response\": "
        self.cycle_tokens[self.cycles] = tokenize(cycle_prompt, count=True)
        # Clear events
        Session.cycle_events = []
        if self._is_primed:
            response = self._run(cycle_prompt)
        else:
            if self.priming_schema != None and Session.history == []:
                try:
                    response = self.priming_schema
                    self.cycle_tokens[self.cycles] += tokenize(str(response), count=True)
                    self.session_tokens += self.cycle_tokens[self.cycles]
                    self._is_primed = True
                except:
                    raise log(LogType.error, f"Priming schema for {self.name} is invalid!\nTry validating with:\nhttps://jsonformatter.curiousconcept.com/")
            else:
                response = self._run(cycle_prompt)  

        # Check if we're past ctx limit, remove as many cycles as needed to clear ctx window
        if self._ctx_limit():
            while self._ctx_limit():
                oldest = Session.history.pop(0)
                cycle = list(oldest.keys())[0]
                self.session_summary.append(oldest[cycle]["cognitive_response"]["cycle_summary"])
                self.session_tokens -= self.cycle_tokens[int(cycle[6:])] # Remove `cycle_`

        # And then we run funcs and append
        for function in response["functions"]:
            func_name = function["name"]
            try:
                func_args = function["arguments"]
            except:
                func_args = {}
            result = execute_function(func_name, **func_args)
            if result != "None":
                Session.add_event(f"{func_name} function", f"Function result: {result}")

        # Rebuild cycle schema, append/save, restart
        cycle = literal_eval(cycle_prompt + str(response) + "}}")

        Session.history.append(cycle)
        # log(LogType.debug, f"Session Tokens: {self.session_tokens}/{self.working_ctx}")
        session_manager.save_cycle(f"{self._persona_cycles_path}/{self.cycles}.json", cycle)
        
        if Session.exit:
            sys.exit()
        else:
            self.parse(override_responses=override_responses)