from colorama import Back, Fore, Style
from datetime import datetime
import pkg_resources
import subprocess
import time
import re
import random
import os
from pathlib import Path
import tarfile
import zipfile
import sys
from typing import Generator
import string
import inspect

def percent_of_string(string: str, percentage: int = 30):
    count = len(string)
    return string[:int((count / 100) * percentage)]

def percent(num: int, perc: int):
    decimal = perc / 100
    return num * decimal

def capfirst(string):
    """
    Alternative to `capitalize()`, preserves letter case.
    """
    if not string:
        return string
    return string[0].upper() + string[1:]

def install_dependencies(dependencies):
    """
    Install dependencies tuple using pip.
    
    Example: [("numpy", "1.19.5"), ("requests", None), ("matplotlib", "3.4.2")]
    """
    for dependency, version in dependencies:
        try:
            pkg_resources.get_distribution(dependency)
            #log(LogType.warning, f"[Dependency Installer] {dependency} is already installed.")
        except pkg_resources.DistributionNotFound:
            try:
                if version:
                    _dependency = f"{dependency}=={version}"
                else:
                    log(LogType.warning, f"[Dependency Installer] Version not specified for {dependency}. Installing latest...")
                    _dependency = dependency
                    
                subprocess.run(["pip", "install", _dependency], check=True)
                log(LogType.system, f"[Dependency Installer] Installed {dependency}.")
            except subprocess.CalledProcessError as e:
                log(LogType.error, f"[Dependency Installer] Error installing {dependency}: {e}")
                return
            except ValueError as ve:
                print(ve)
                return

def parse_all(content:list, function, **kwargs):
    """
    Parse all items in a list to the given function.
    """
    results = []
    i = 1
    for chunk in content:
        result = function(chunk, **kwargs)
        results.append(result)
        log(LogType.system, f"Parser Batch: {i}/{len(content)}")
        i =+ 1
    return results

def rand_seed():
    return random.randrange(1, 999999999)

def clean_scrape(scrape:str|list, as_string:bool=False):
    if isinstance(scrape, list):
        clean = []
        for s in scrape:
            clean.append(re.sub(r"\s+", " ", s).strip())
        if as_string:
            clean = "\n".join(clean)
    else:
        clean = re.sub(r"\s+", " ", scrape)
    return clean

def get_dir(folder: str, create_if_missing: bool = True):
    dir_path = Path(__file__).resolve().parent / folder
    if create_if_missing:
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    else:
        return dir_path.exists()

def get_caller_path():
    frame = inspect.stack()[1]
    caller = frame.filename
    caller_script = os.path.abspath(caller)
    caller_path = os.path.dirname(caller_script)
    return caller_path

def download_folder(path: str = None):
    main_dir = Path(__file__).resolve().parent
    download_dir = main_dir / "downloads"
    
    if path is None:
        return download_dir
    
    folders = path.split("/")
    for folder in folders:
        download_dir /= folder
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir

def split_paragraph(paragraph:str):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', paragraph)
    total_chars = sum(len(sentence) for sentence in sentences)
    middle_point = total_chars // 2
    current_position = 0
    first_half = ""
    
    for sentence in sentences:
        current_position += len(sentence)
        if current_position >= middle_point:
            first_half = paragraph[:paragraph.index(sentence) + len(sentence)]
            second_half = paragraph[paragraph.index(sentence) + len(sentence):]
            break
        
    return first_half, second_half

def read_from_folder(path, extension=None):
    files = []
    for file in os.listdir(path):
        if extension != None:
            if file.endswith(extension):
                files.append(file)
        else:
            files.append(file)
    return files


class Time:
    def compact():
        """
        MM-DD-YYYY H:M:S
        """
        return datetime.now().strftime("%m/%d/%Y %H:%M:%S")

    def day():
        """
        Name of day
        """
        return datetime.now().strftime("%A")

    def date():
        """
        Name, MM DD YYYY
        """
        return datetime.now().strftime("%A, %B %d %Y")

    def time():
        """
        HH:MM:SS
        """
        return datetime.now().strftime("%H:%M:%S")
    
    def full():
        """
        Name, MM DD YYYY, HH:MM:SS
        """
        return datetime.now().strftime("%A, %B %d %Y, %H:%M:%S")

def substring(text:str, start_str:str=None, end_str:str=None):
    if start_str is None and end_str is None:
        return text
    
    start_index = 0 if start_str is None else text.find(start_str)
    if start_index == -1:
        start_index = 0
    if start_str is not None:
        start_index += len(start_str)
        
    end_index = len(text) if end_str is None else text.find(end_str, start_index)
    if end_index == -1:
        end_index = len(text)
        
    return text[start_index:end_index]

def string_to_kwargs(string):
    pattern = r'(\w+)\s*=\s*(\'[^\']*\'|\"[^\"]*\"|[^\s]+)'
    matches = re.findall(pattern, string)
    result = {}
    
    for match in matches:
        key = match[0]
        value = match[1]
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]
        result[key] = value
    return result

def kwargs_to_string(kwargs: dict):
    return ", ".join([f"{key} = {repr(value)}" for key, value in kwargs.items()])

def unzip(target:str, suppress_log=False):
    valid_formats = [".tar.gz", ".zip"]
    
    for format in valid_formats:
        if target.endswith(format):
            target_file = Path(__file__).resolve().parent / "downloads" / target
            target_folder = download_folder(target[:-len(format)])
            os.chdir(target_folder)
            try:
                if format == ".tar.gz":
                    with tarfile.open(target_file, "r:gz") as tar:
                        tar.extractall()
                elif format == ".zip":
                    with zipfile.ZipFile(target_file) as zipf:
                        zipf.extractall()
                filename = target.rsplit("/", 1)[-1]
                if not suppress_log:
                    log(LogType.system, f"[Unzip] File {filename} extracted.", is_stream=False)
            finally:
                os.chdir(os.path.dirname(os.path.abspath(__file__)))
    return target_folder

def dict_to_formatted_string(dictionary: dict, values_only: bool = False) -> str:
    result = []
    for key, value in dictionary.items():
        if isinstance(value, list):
            value_str = ", ".join(map(str, value))
        else:
            value_str = str(value)
        if values_only:
            formatted_line = value_str
        else:
            formatted_line = f"{key.replace('_', ' ').capitalize()}: {value_str}"
        result.append(formatted_line)
    return "\n".join(result)

def unsnake(content: str, capitalize_words: bool = True):
    as_string = content.replace("_", " ")
    if capitalize_words:
        return string.capwords(as_string)
    else:
        return as_string

class LogType:
    error = "⛔", "ERROR", [Back.RED, Fore.WHITE]
    warning = "⚠️", "WARNING", [Back.YELLOW, Fore.BLACK]
    system = "💻", "System", [Back.CYAN, Fore.WHITE]
    response = "💬", "Response", [Back.BLUE, Fore.LIGHTWHITE_EX]
    think = "🧠", "Thinking", [Back.LIGHTMAGENTA_EX, Fore.LIGHTWHITE_EX]
    exploring = "🧭", "Exploring", [Back.LIGHTGREEN_EX, Fore.BLACK]
    action = "⚙️", "Action", [Back.GREEN, Fore.BLACK]
    learn = "✍️", "Learning", [Back.BLUE, Fore.WHITE]
    recall = "📖", "Recalling", [Back.BLUE, Fore.WHITE]
    web = "🌐" "Web", [Back.YELLOW, Fore.BLACK]
    boot_sequence = "", "", [Back.CYAN, Fore.WHITE]
    debug = "🐛", "Debug", [Back.WHITE, Fore.BLACK]
    download = "⬇️", "Downloading", [Back.LIGHTGREEN_EX, Fore.BLACK]
    delete = "🗑️", "Deleting", [Back.LIGHTRED_EX, Fore.WHITE]

def stream_text(content, stream_speed=0.005):
    for i in range(0, len(content), 2):
        print(content[i:i+2], end="", flush=True)
        time.sleep(stream_speed)

def log(log_type: LogType, str_or_generator: str | Generator, with_prefix: bool = False, str_as_stream: bool = False, stream_speed: float = 0.01, updatable_str: bool = False, **kwargs):
    """
    Print colored output to terminal.
    
    If `Generator` is provided, returns joined output.
    
    If using `updatable_str` with a loop, you should log the final item by itself (e,g: "process complete").
    """
    LINE_UP = "\033[1A"
    LINE_CLEAR = "\x1b[2K"
    emoji, prefix, color = log_type
    style = "".join(color)
    prev_char_newline = False
    
    if isinstance(str_or_generator, Generator):
        start = True
        content = []
        while True:
            try:
                chunk = next(str_or_generator)
                if start:
                    if chunk.startswith(" "):
                        pad = ""
                    else:
                        pad = " "
                    if with_prefix:
                        print(f"{style}{emoji}  {prefix}:{pad}", end="")
                    else:
                        print(f"{style}{emoji}:{pad}", end="")
                    start = False
                for char in chunk:
                    if char == "\n":
                        if not prev_char_newline:
                            print(Style.RESET_ALL)
                        prev_char_newline = True
                    else:
                        print(style + char, end="")
                        sys.stdout.flush()
                        prev_char_newline = False
                content.append(chunk)
            except StopIteration:
                print(Style.RESET_ALL)
                return "".join(content)
    else:
        if with_prefix:
            logstr = f"{style}{emoji}   {prefix}: {str_or_generator}{Style.RESET_ALL}"
        else:
            if log_type is LogType.boot_sequence:
                logstr = f"{style}{str_or_generator}{Style.RESET_ALL}"
            else:
                logstr = f"{style}{emoji}   {str_or_generator}{Style.RESET_ALL}".strip()
        
        if str_as_stream:
            stream_text(logstr+"\n", stream_speed=stream_speed)
        else:
            if updatable_str:
                terminal_width = os.get_terminal_size().columns
                if len(logstr) > terminal_width:
                    logstr = logstr[:terminal_width-3] + "..."
                print(logstr.strip())
                print(LINE_UP, end=LINE_CLEAR)
            else:
                print(logstr.strip())

def _shuffle_acronym():
    _m = [
        "Multi-agent",
        "Modulated",
        "Modular",
        "Magical",
        "Malleable",
        "Modifiable",
        "Morphable",
        "Memory-based"
    ]
    _i = [
        "Interactive",
        "Intelligent",
        "Instructive",
        "Integrated",
        "Interfaceable",
        "Instance-based",
        "Independent",
        "Intent-driven"
    ]
    _s = [
        "Synthetic",
        "Structured",
        "Semantic",
        "Source",
        "Simulated",
        "System",
        "Self-aware",
        "Smart"
    ]
    _t = [
        "Tasker",
        "Thinker",
        "Toolset",
        "Troublemaker",
        "Technology",
        "Talent",
        "Topology",
        "Template"
    ]

    m = random.randrange(len(_m))
    i = random.randrange(len(_i))
    s = random.randrange(len(_s))
    t = random.randrange(len(_t))
    if m == 1 and i == 3 and s == 3 and t == 7:
        # Go watch Pantheon :)
        log(LogType.boot_sequence, _boot_padding(""))
        log(LogType.boot_sequence, _boot_padding("Evolution tends to move at its own pace,"))
        log(LogType.boot_sequence, _boot_padding("but it's always in motion."))
        log(LogType.boot_sequence, _boot_padding("No one can stop the future,"))
        log(LogType.boot_sequence, _boot_padding("even someone determined to bring it about."))
        log(LogType.boot_sequence, _boot_padding(""))
    return f"[{_m[m]} {_i[i]} {_s[s]} {_t[t]}]"

def _boot_padding(string: str):
    total_padding = 50 - len(string)
    if total_padding <= 0:
        return string
    
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding
    
    padded_string = " " * left_padding + string + " " * right_padding
    return padded_string
