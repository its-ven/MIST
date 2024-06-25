from inspect import signature, isfunction
import os
import importlib.util
from utils import log, LogType, kwargs_to_string
import settings
from api import SchemaValue
from ast import literal_eval

registered_modules = {}

DISABLED_MODULES = settings.disabled_modules

def register(description: str):
    """
    Register a function for agent usage.
    
    It is recommended to name arguments literally.
    
    `description`: A brief description for the agent to understand the function.
    """
    def decorator(f):
        def wrapped(**kwargs):
            return f(**kwargs)
        wrapped.__signature__ = signature(f)
        wrapped.description = description
        return wrapped
    return decorator

def register_unsafe(description: str):
    """
    Register an unsafe function for agent usage. Requires user confirmation before execution.
    
    It is recommended to name arguments literally.
    
    `description`: A brief description for the agent to understand the function.
    """
    def decorator(f):
        def wrapped(**kwargs):
            return f(**kwargs)
        wrapped.__signature__ = signature(f)
        wrapped.is_unsafe = True
        wrapped.description = description
        return wrapped
    return decorator

def load():
    global registered_modules
    registered_modules.clear()
    modules_folder = "./modules"
    for root, dirs, files in os.walk(modules_folder):
        for dir_name in dirs:
            module_path = os.path.join(root, dir_name, "main.py")
            if os.path.exists(module_path):
                module_name = dir_name
                if module_name not in DISABLED_MODULES:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    functions = []
                    total_functions = 0

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isfunction(attr) and hasattr(attr, "__signature__"):
                            total_functions += 1

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isfunction(attr) and hasattr(attr, "__signature__"):
                            is_unsafe = getattr(attr, "is_unsafe", False)
                            description = getattr(attr, "description", "")
                            function_root = {
                                "root": module.__name__,
                                "name": attr_name,
                                "func": attr,
                                "args": str(attr.__signature__),
                                "unsafe": is_unsafe,
                                "description": description
                            }
                            functions.append(function_root)

                    log(LogType.system, f"[Modules] Loaded {module_name.capitalize()}", with_prefix=False)
                    registered_modules[module_name] = functions

def get_functions(module_or_specific: str | list = None, for_prompt: bool = False, **kwargs) -> str | list:
    """
    `module_or_specific`
    - `str`: Get all functions from stated module.
    
    - `list`: Get explicit function(s) from any module.
    
    If neither is specified, return all functions.
    """
    if module_or_specific is None:
       container = []
       for module in registered_modules.values():
           for func in module:
               container.append(func)
    elif isinstance(module_or_specific, str):
        container = registered_modules[module_or_specific]
    elif isinstance(module_or_specific, list):
        container = []
        for module in registered_modules.values():
            for func in module:
                if func['name'] in module_or_specific:
                    container.append(func)      
    if for_prompt:
        entries = []
        for function in container:
            desc = function['description']
            # For better prompt consistency
            if not desc.endswith("."):
                desc += "."
            entries.append(f"- `{function['name']}{function['args']}`: {desc}")
        return "\n".join(entries)
    
    if kwargs:
        if "properties" in kwargs:
            funcs = {}
            for func in container:
                properties = {}
                for property in kwargs['properties']:
                    properties[property] = func[property]
                funcs[func['name']] = properties
            return funcs
    else:
        return container



def execute_function(function_name: str, **kwargs):
    for module in registered_modules.values():
        for function in module:
            if function['name'] == function_name:
                if function['unsafe']:
                    user_input = input(f"function '{function_name}({kwargs_to_string(**kwargs)})' is unsafe. Continue? (y/n): ")
                    if user_input.lower() != 'y':
                        log(LogType.warning, err)
                        return f"User aborted unsafe function '{function_name}'."
                try:
                    result = function['func'](**kwargs)
                    return result
                except Exception as e:
                    err = f"ERROR: Function {function_name} failed to execute ({str(e)})"
                    log(LogType.warning, err)
                    return err


class Toolkit:
    """
        Initialize a toolkit of registered functions.
        
        Can be dynamically changed with `add()` and `remove()`.
        
        - `str`: Add all from module name.
        
        - `list`: Add one or multiple specific functions from all modules. 
        
        - Adds all modules if `module_or_specific` not specified.
    """
    def __init__(
        self,
        module_or_specific: str | list = None
    ):
        self.functions = []
        # Load funcs now if they weren't before
        if registered_modules == {}:
            load()
        try:
            self.functions.extend(get_functions(module_or_specific))
        except Exception as e:
            raise log(LogType.error, f"[Toolkit] {e}")
    
    def add(self, module_or_specific: str | list):
        """
            - `str`: Add all from module name.
            
            - `list`: Add one or multiple specific functions from all modules. 
        """
        new_funcs = get_functions(module_or_specific)
        existing_func_names = {func["name"] for func in self.functions}
        self.functions.extend([func for func in new_funcs if func["name"] not in existing_func_names])
    
    def remove(self, module_or_specific: str | list):
        """
            - `str`: Remove all from module name.
        
            - `list`: Remove one or multiple specific functions from all modules. 
        """
        funcs_to_remove = get_functions(module_or_specific)
        funcs_to_remove_names = {func["name"] for func in funcs_to_remove}
        self.functions = [func for func in self.functions if func["name"] not in funcs_to_remove_names]
    
    def _descriptions(self):
        return [func["description"] for func in self.functions]
    
    def _names(self):
        return [func["name"] for func in self.functions]
    
    def _prompt(self, **kwargs):
        return get_functions(self._names(), for_prompt=True, **kwargs)
    
    def _schema(self):
        schema_dict = {}
        for func in self.functions:
            func_name = func["name"]
            func_signature = signature(func["func"])
            properties = {}
            for param in func_signature.parameters.values():
                if param.annotation == str:
                    param_type = SchemaValue.string
                elif param.annotation == int:
                    param_type = SchemaValue.integer
                elif param.annotation == bool:
                    param_type = SchemaValue.boolean
                elif param.annotation == list[str]:
                        param_type = SchemaValue.string_list
                elif param.annotation == list[int]:
                        param_type = SchemaValue.integer_list
                else:
                    param_type = {"type": "string"}
                properties[param.name] = param_type

            schema_dict[func_name] = {
                "type": "object",
                "properties": properties
            }
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": schema_dict
            }
        }
        return schema