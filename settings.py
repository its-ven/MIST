from dotenv import load_dotenv, dotenv_values, get_key, set_key
from datetime import datetime, timedelta
from utils import get_dir
from ast import literal_eval

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
    "# Flash attention (for low-end systems)",
    "LLAMA_FLASH_ATTENTION=True",
    "# How many layers to offload to GPU",
    "LLAMA_N_GPU_LAYERS=50",
    "",
    "# Name of default Persona",
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
    "CORE_TEMPERATURE = 0.7",
    "CORE_TOP_P = 0.6",
    "CORE_MIN_P = 0.5",
    "CORE_FREQUENCY_PENALTY = 0.7",
    "CORE_PRESENCE_PENALTY = 0.4",
    "# Disable any given word/string. Useful to handle hallucinations.",
    "CORE_LOGIT_BIAS = []",
    "",
    "# Instruct model:",
    "INSTRUCT_MODEL='GGUF_PATH'",
    "INSTRUCT_SIZE=4096",
    "",
    "# Disable modules using string list.",
    "DISABLED_MODULES=[]",
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
disable_splash = literal_eval(config.get("DISABLE_SPLASH"))
llama_build_type = config.get("LLAMA_BUILD_TYPE").replace(".zip", "")
llama_host = config.get("LLAMA_HOST")
llama_port = literal_eval(config.get("LLAMA_PORT"))
llama_auto_update = literal_eval(config.get("LLAMA_AUTO_UPDATE"))
llama_flash_attention = literal_eval(config.get("LLAMA_FLASH_ATTENTION"))
llama_n_gpu_layers  = literal_eval(config.get("LLAMA_N_GPU_LAYERS"))

default_persona = config.get("DEFAULT_PERSONA")
override_responses = literal_eval(config.get("OVERRIDE_RESPONSES"))

long_context_model = config.get("LONG_CONTEXT_MODEL")
long_context_size = literal_eval(config.get("LONG_CONTEXT_SIZE"))

core_model = config.get("CORE_MODEL")
core_size = literal_eval(config.get("CORE_SIZE"))
core_temperature = literal_eval(config.get("CORE_TEMPERATURE"))
core_top_p = literal_eval(config.get("CORE_TOP_P"))
core_min_p = literal_eval(config.get("CORE_MIN_P"))
core_frequency_penalty = literal_eval(config.get("CORE_FREQUENCY_PENALTY"))
core_presence_penalty = literal_eval(config.get("CORE_PRESENCE_PENALTY"))
core_logit_bias = literal_eval(config.get("CORE_LOGIT_BIAS"))

instruct_model = config.get("INSTRUCT_MODEL")
instruct_size = literal_eval(config.get("INSTRUCT_SIZE"))

disabled_modules = literal_eval(config.get("DISABLED_MODULES"))
llama_latest_build = config.get("LLAMA_LATEST_BUILD")
llama_last_check = config.get("LLAMA_LAST_CHECK")

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
