import settings
from enum import Enum
from ast import literal_eval
import requests
from server import load, Model
import re
import json
from typing import Generator
from utils import log, LogType
import traceback

host = f"{settings.llama_host}:{str(settings.llama_port)}"
completion_endpoint = f"{host}/completion"
chat_endpoint = f"{host}/v1/chat/completions"
infill_endpoint = f"{host}/infill"
tokenizer_endpoint = f"{host}/tokenize"

# Strip any escaped stops.
GLOBAL_STOPS = [
    "<|eot_id|>",
    "<|im_end>",
    "<|end|>",
    "<|calc|>",
    "<|/data|>",
    "</s>",
    "[INST]",
    "<|assistant|>"
]

def _format_prompt(prompt: str, format_codeblocks: bool = True) -> str:
    """Format the prompt by removing leading indentation and processing code blocks."""
    def has_codeblock(s: str) -> bool:
        return s.count("```") >= 2

    def strip_indentation(text: str) -> str:
        return re.sub(r"^ {4,}", '', text, flags=re.MULTILINE)

    try:
        if has_codeblock(prompt) and format_codeblocks:
            chunks = prompt.split("```")
            text_chunks = chunks[::2]
            code_chunks = chunks[1::2]

            formatted_text_chunks = [strip_indentation(chunk) for chunk in text_chunks]
            formatted_code_chunks = []

            for code_chunk in code_chunks:
                lines = code_chunk.split("\n")
                if len(lines) > 1 and lines[0].strip() == '':
                    lines = lines[1:]
                whitespace_count = min((len(line) - len(line.lstrip(' '))) for line in lines if line.strip())
                formatted_code_chunk = "\n".join([line[whitespace_count:] if line.strip() else line for line in lines])
                formatted_code_chunks.append(formatted_code_chunk)

            result = "".join(
                f"{text_chunk}```{code_chunk}```" if i < len(code_chunks) else text_chunk
                for i, text_chunk in enumerate(formatted_text_chunks)
                for code_chunk in [formatted_code_chunks[i]] if i < len(formatted_code_chunks)
            )
        else:
            result = strip_indentation(prompt).strip()
    except Exception:
        result = strip_indentation(prompt).strip()
    return result

class SchemaValue:
    string = {"type": "string", "minLength": 1}
    integer = {"type": "integer"}
    boolean = {"type": "boolean"}

    @classmethod
    def _list(cls, obj, min_items: int = None, max_items: int = None):
        schema = {"type": "array", "items": obj}
        if min_items is not None:
            schema["minItems"] = min_items
        if max_items is not None:
            schema["maxItems"] = max_items
        return schema

    @classmethod
    def regex_pattern(cls, pattern: str):
        return {"type": "string", "pattern": pattern}
    
    @classmethod
    def regex_list(cls, pattern: str, min_items: int = None, max_items: int = None):
        return cls._list(cls.regex_pattern(pattern), min_items=min_items, max_items=max_items)

    @classmethod
    def string_list(cls, min_items: int = None, max_items: int = None):
        return cls._list(cls.string, min_items, max_items)

    @classmethod
    def integer_list(cls, min_items: int = None, max_items: int = None):
        return cls._list(cls.integer, min_items, max_items)

    @classmethod
    def dict_list(cls, keys: dict):
        return cls._list({"type": "object", "properties": keys, "required": list(keys.keys())})

    @classmethod
    def dictionary(cls, **keys):
        return {"type": "object", "properties": keys}

    @classmethod
    def function_schema(cls):
        return {
            "type": "object",
            "properties": {
                "name": cls.string,
                "arguments": {"type": "object", "additionalProperties": True}
            },
            "required": ["name", "arguments"]
        }

    @classmethod
    def functions_list(cls):
        return cls._list(cls.function_schema(), min_items=1)

def make_schema(required: list[str] = [], **keys):
    """
    Example usage in API call:
    
    `json_schema=make_schema(my_string_key=SchemaValue.string, my_int_key=SchemaValue.integer, my_custom_key=my_custom_schema)`
    """    
    schema = {
        "type": "object",
        "properties": keys,
        "required": required if required else list(keys.keys())
    }
    return schema

class SpecialReturn:
    def __init__(self, return_type=None, n_probs=None):
        self.return_type = return_type
        self.n_probs = n_probs

    # Probabilities printed as tree graphs.
    @staticmethod
    def probability_trees(n_probs: int):
        return SpecialReturn(return_type="probability_trees", n_probs=n_probs + 1) # Return +1 to account for root
    
    @staticmethod
    def probabilities(n_probs: int):
        return SpecialReturn(return_type="probabilities", n_probs=n_probs)
    
    @staticmethod
    def completion_tokens():
        return SpecialReturn(return_type="completion_tokens")
    
    @staticmethod
    def prompt_tokens():
        return SpecialReturn(return_type="prompt_tokens")
    
    @staticmethod
    def total_tokens():
        return SpecialReturn(return_type="total_tokens")
    
    # Everything
    @staticmethod
    def full():
        return SpecialReturn(return_type="full")

def _logprob_trees(logprobs: list, n_decimals: int = 3):
        trees = []
        for logprob in logprobs:
            root = str(logprob["content"])
            branch = "|-"
            branch_length = 0
            sub_branch = []
            
            if logprob["probs"]:
                root_prob = next((prob for prob in logprob["probs"] if prob["tok_str"].strip() == root.strip()), None)
                root_value = round(root_prob["prob"], n_decimals) if root_prob else None
            else:
                root_value = None
            
            for prob in sorted(logprob["probs"], key=lambda x: x["prob"], reverse=True):
                if prob["tok_str"].strip() == root.strip():
                    continue
                
                twig = branch + ("-" * branch_length)
                token = prob["tok_str"]
                probability = round(prob["prob"], n_decimals)
                
                sub_branch.append(f"{twig}> \"{token}\" ({probability})")
                branch_length += 1
                    
            sub_branch = "\n".join(sub_branch)
            trees.append(f"\"{root}\" ({root_value})\n{sub_branch}")
                
        return "\n\n".join(trees)

def _stream(response):
    for chunk in response.iter_lines():
        if chunk:
            chunk_data = json.loads(chunk.decode('utf-8')[6:])  # Remove 'data: ' prefix
            if "choices" in chunk_data and chunk_data["choices"]:
                delta = chunk_data["choices"][0].get("delta", {})
                if "content" in delta:
                    content = str(delta["content"])
                    yield content

def tokenize(string: str, count: bool = False) -> list[int]:
    load()
    response = requests.post(tokenizer_endpoint, json={"content": string}).json()
    if count:
        return len(response["tokens"])
    return response["tokens"]

def completion(

    prompt: str,
    model: Model = Model.core,
    special_return: SpecialReturn = None,
    stream: bool = False,
    skip_formatting = False,
    **kwargs
):
    load(model)
    params = {}
    params["prompt"] = prompt if skip_formatting else _format_prompt(prompt)
    if kwargs:
        for k, v in kwargs.items():
            if k == "max_tokens":
                params["n_predict"] = v
            else:
                params[k] = v
    try:
        params["stop"] += GLOBAL_STOPS
    except:
        params["stop"] = GLOBAL_STOPS
    if special_return and special_return.return_type in ["probabilities", "probability_trees"]:
        params["n_probs"] = special_return.n_probs
        
    if stream:
        params["stream"] = True
        _response = requests.post(completion_endpoint, json=params, stream=True)
        return _stream(_response)
    else:
        _response = requests.post(completion_endpoint, json=params).json()
        if special_return:
            if special_return.return_type == "probability_trees":
                if "completion_probabilities" in _response:
                    special = _logprob_trees(_response["completion_probabilities"], kwargs.get("n_decimals", 3), kwargs.get("as_menus", False))
                else:
                    special = "No completion probabilities returned in the response."
            elif special_return.return_type == "probabilities":
                special = _response.get("completion_probabilities", "No completion probabilities returned in the response.")
            elif special_return.return_type == "completion_tokens":
                special = _response["tokens_predicted"]
            elif special_return.return_type == "prompt_tokens":
                special = _response["tokens_evaluated"]
            elif special_return.return_type == "total_tokens":
                special = _response["tokens_predicted"] + _response["tokens_evaluated"]
            elif special_return.return_type == "full":
                special = _response

        content = _response["content"].strip()
        if "json_schema" in kwargs:
            try:
                content = json.loads(content)
            except Exception:
                log(LogType.warning, f"[API] Error generating response! Trying again... ({traceback.format_exc()})")
                completion(prompt, special_return, stream, **kwargs)
        if special_return:
            return content, special
        else:
            return content

def response(
    system: str,
    prompt: str,
    model: Model = Model.core,
    history: list = [],
    special_return: SpecialReturn = None,
    stream: bool = False,
    **kwargs
) -> dict | Generator:
    """
    `history`: OpenAI-style dict list for forming conversation history. You can append to a list with `append_to_history`.
    
    `special_return`: Refer to `SpecialReturn` class. Used for debugging or info.
    
    `stream`: returns an iterable generator.
    """
    load(model)
    turn = [
        {
            "role": "system",
            "content": _format_prompt(system)
        },
        {
            "role": "user",
            "content": _format_prompt(prompt)
        }
    ]
    params = {}

    if history:
        params["messages"] = history + turn
    else:
        params["messages"] = turn
        
    if kwargs:
        for k, v in kwargs.items():
            if k == "max_tokens":
                params["n_predict"] = v
            else:
                params[k] = v
    try:
        params["stop"] += GLOBAL_STOPS
    except:
        params["stop"] = GLOBAL_STOPS
        
    if special_return and special_return.return_type in ["probabilities", "probability_trees"]:
        params["n_probs"] = special_return.n_probs
        
    if stream:
        params["stream"] = True
        _response = requests.post(chat_endpoint, json=params, stream=True)
        return _stream(_response)
    else:
        _response = requests.post(chat_endpoint, json=params).json()
        if special_return:
            if special_return.return_type == "probability_trees":
                if "completion_probabilities" in _response:
                    special = _logprob_trees(_response["completion_probabilities"], kwargs.get("n_decimals", 3), kwargs.get("as_menus", False))
                else:
                    special = "No completion probabilities returned in the response."
            elif special_return.return_type == "probabilities":
                special = _response.get("completion_probabilities", "No completion probabilities returned in the response.")
            elif special_return.return_type == "completion_tokens":
                special = _response["usage"]["completion_tokens"]
            elif special_return.return_type == "prompt_tokens":
                special = _response["usage"]["prompt_tokens"]
            elif special_return.return_type == "total_tokens":
                special = _response["usage"]["total_tokens"]
            elif special_return.return_type == "full":
                special = _response

        content = _response["choices"][0]["message"]["content"].strip()
        if "json_schema" in kwargs:
            try:
                content = json.loads(content)
            except Exception as e:
                log(LogType.warning, f"[API] Error generating response! Trying again... ({e})")
                print(traceback.print_exc())
                return response(model, system, prompt, history, special_return, stream, **kwargs)

        if special_return:
            return content, special
        else:
            return content


def append_to_history(history: list, role: str, content: str):
    history.append({"role": role, "content": content})

def get_history(history: list, as_string: bool = False):
    _history = []
    for entry in history:
        role = str(entry["role"])
        content = str(entry["content"])
        _history.append(f"{role.capitalize()}: {content}")
    if as_string:
        return "\n".join(_history)
    else:
        return _history

# NOTE: Broken??
#def infill(prefix: str, suffix: str, **kwargs):
#    load(kwargs.get("model", Model.reasoning))
#    params = {
#        "input_prefix": prefix,
#        "input_suffix": suffix,
#        "temperature": kwargs.get("temperature", 0.7),
#        "top_p": kwargs.get("top_p", 0.2),
#        "min_p": kwargs.get("min_p", 0.5),
#        **kwargs
#    }
#    response = requests.post(infill_endpoint, json=params).json()
    