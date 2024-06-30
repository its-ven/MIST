import subprocess
import settings
import os
import requests
from utils import unzip, log, LogType, get_dir, substring
import shutil
from tqdm import tqdm
import platform
import time
    
current_model = None
instance = None

class Model:
    core = [settings.core_model, settings.core_size]
    long_context = [settings.long_context_model, settings.long_context_size]
    instruct = [settings.instruct_model, settings.instruct_size]

def llama_binary(binary: str):
    return f"{binary}.exe" if platform.system() == "Windows" else binary

def override_tokenizer(model: str):
    if "llama-3" in model.lower() or "llama3" in model.lower():
        return ["--override-kv", "tokenizer.ggml.pre=str:llama3"]
    else:
        return []

def _download(download_url: str):
    build = requests.get(download_url, stream=True)
    filename = download_url.split("/")[-1]
    zip_path = get_dir("llamacpp") / filename

    file_size = int(build.headers.get("content-length", 0))
    block_size = 1024
    
    with tqdm(total=file_size, unit="B", unit_scale=True) as progress:
        with open(zip_path, "wb") as file:
            for data in build.iter_content(block_size):
                progress.update(len(data))
                file.write(data)

    tmp_folder = unzip(str(zip_path), suppress_log=True)
    for root, dirs, files in os.walk(tmp_folder):
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(get_dir("llamacpp"), file)
            shutil.move(src_file, dst_file)
    os.remove(zip_path)
    shutil.rmtree(tmp_folder)

def update():
        try:
            url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
            response = requests.get(url)
            data = response.json()
            latest_build = data["name"]
            if settings.llama_latest_build != latest_build:    
                for asset in data["assets"]:
                    if "cuda" in settings.llama_build_type:
                        cuda_ver = substring(settings.llama_build_type, "cuda-", "-")
                        if "cudart" in asset["name"] and cuda_ver in asset["name"]:
                            if not get_dir("llamacpp", create_if_missing=False):
                                log(LogType.download, "[Server] Downloading CUDA binaries...")
                                download_url = str(asset["browser_download_url"])
                                _download(download_url)
                    if settings.llama_build_type in asset["name"]:
                        log(LogType.download, f"[Server] Updating llama.cpp ({latest_build})...", with_prefix=False)
                        download_url = str(asset["browser_download_url"])
                        _download(download_url)
                        settings.set_llama_build(latest_build)
                        break
                else:
                    raise log(LogType.error, f"[Server] llama.cpp build {settings.llama_build_type} not found! Check spelling?")
        except Exception as e:
            log(LogType.warning, f"[Server] Could not download llama.cpp update! ({e})", is_stream=False)

def is_running():
    return True if instance != None else False

def close():
    if is_running():
        instance.terminate()
    
def load(model: Model = Model.core):
    global current_model, instance
    if settings.llama_update():
        if is_running():
            close()
        update()
        time.sleep(1)
        load(model)
    
    server_ex = llama_binary("llama-server")
    args = [
            os.path.join(get_dir("llamacpp"), server_ex),
            "-m", model[0],
            "--mlock",
            "--port", str(settings.llama_port),
            "-v",
            "-c", str(model[1])
        ]
    
    if settings.llama_flash_attention:
        args.append("-fa")
    if settings.llama_n_gpu_layers > 0:
        args.extend(["-ngl", str(settings.llama_n_gpu_layers)])

    # Restart server if new model
    if model[0] != current_model:
        if is_running():
            close()
        current_model = model[0]
        exec = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        instance = exec
