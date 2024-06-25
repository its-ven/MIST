from dotenv import load_dotenv, dotenv_values, get_key, set_key
from datetime import datetime, timedelta
from utils import Time, get_dir

CONFIG_TEMPLATE = [
    "# Disable splash screen",
    "DISABLE_SPLASH=False",
    "",
    "# Set llama.cpp build:"
    "# 1. Go to https://github.com/ggerganov/llama.cpp/releases",
    "# 2. Select your build type ('llama-bXXXX-bin-BUILD_TYPE.zip')",
    "# Example: win-cuda-cu12.2.0-x64",
    "LLAMA_BUILD_TYPE='win-cuda-cu12.2.0-x64'",
    "",
    "# Set llama.cpp host and port.",
    "# Default: http//localhost, 8080",
    "LLAMA_HOST='http://localhost'",
    "LLAMA_PORT=8080",
    "",
    "# Auto-update llama.cpp binaries on runtime.",
    "LLAMA_AUTO_UPDATE=True",
    "",
    "# Name of default Persona JSON",
    "DEFAULT_PERSONA='MIST'",
    "# Get prompted to accept or override responses"
    "OVERRIDE_RESPONSES=False"
    "",
    "# Set path of GGUF files and context sizes based on your RAM/VRAM.",
    "# Example path: 'C:/Your Models/Llama-3-8B-Instruct.Q5_K_S.gguf'",
    "# It is not recommended you set context sizes below 4096.",
    "",
    "# Summarization, scraping, etc:",
    "LONG_CONTEXT_MODEL='GGUF_PATH'",
    "LONG_CONTEXT_SIZE = 16384",
    "",
    "# Core model:",
    "CORE_MODEL='GGUF_PATH'",
    "CORE_SIZE=8192",
    "",
    "# Instruct model:",
    "INSTRUCT_MODEL='GGUF_PATH'",
    "INSTRUCT_SIZE=4096",
    "",
    "# Disable any module by separating module names with commas (default: None).",
    "DISABLED_MODULES=None",
    "",
    "# These are automatically set.",
    "LLAMA_LATEST_BUILD='b0000'",
    "LLAMA_LAST_CHECK='2024-01-02 03:04:05'"
]

def load():
    dotenv_path = ".env"
    dotenv_exists = load_dotenv(dotenv_path)
    if not dotenv_exists:
        with open(dotenv_path, "w") as file:
            for line in CONFIG_TEMPLATE:
                file.write(f"{line}\n")
        llama_dir = get_dir("llamacpp")
        if not llama_dir.exists():
            llama_dir.mkdir(parents=True)

load()

config = dotenv_values(".env")

def _get_config_value(key, default=None, parse_func=str):
    return parse_func(config.get(key, default))

disable_splash = _get_config_value("DISABLE_SPLASH", False, bool)
llama_build_type = _get_config_value("LLAMA_BUILD_TYPE").replace(".zip", "")
llama_host = _get_config_value("LLAMA_HOST")
llama_port = _get_config_value("LLAMA_PORT")
llama_auto_update = _get_config_value("LLAMA_AUTO_UPDATE", True, bool)
default_persona = _get_config_value("DEFAULT_PERSONA")
override_responses = _get_config_value("OVERRIDE_RESPONSES", False, bool)
long_context_model = _get_config_value("LONG_CONTEXT_MODEL")
long_context_size = _get_config_value("LONG_CONTEXT_SIZE", 16384, int)
core_model = _get_config_value("CORE_MODEL")
core_size = _get_config_value("CORE_SIZE", "8192", int)
instruct_model = _get_config_value("INSTRUCT_MODEL")
instruct_size = _get_config_value("INSTRUCT_SIZE", 4096, int)
disabled_modules = _get_config_value("DISABLED_MODULES", "").split(", ") if config.get("DISABLED_MODULES") else None
llama_latest_build = _get_config_value("LLAMA_LATEST_BUILD")
llama_last_check = _get_config_value("LLAMA_LAST_CHECK")

def llama_update():
    global llama_last_check, llama_auto_update
    if llama_auto_update:
        last_check = datetime.strptime(llama_last_check, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - last_check
        delta = timedelta(minutes=120)
        if diff >= delta:
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            set_key(".env", "LLAMA_LAST_CHECK", now_str)
            llama_last_check = now_str
            return True
        else:
            return False
    else:
        return False

def set_llama_build(build: str):
    set_key(".env", "LLAMA_LATEST_BUILD", build)
