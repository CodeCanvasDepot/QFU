#from dotenv import load_dotenv
import discord
import os
from discord.ext import commands
from discord.ext.commands import check
import json
from dotenv import load_dotenv
from datetime import datetime
import time
import random

# Load .env file
load_dotenv()
echo_enabled = True  # Default: echo is on


# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

# Ensure logs folder exists
LOGS_DIR = os.path.join(BASE_DIR, "logs")

user_directories = {}

# Add this at the top with your imports
STATE_FILE = os.path.join(CONFIG_DIR, 'terminal_state.json')







def init_terminal_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f:
            json.dump({'cwd': DATA_DIR}, f)
    else:
        # Validate the stored cwd
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        if not os.path.exists(state.get('cwd', '')):
            with open(STATE_FILE, 'w') as f:
                json.dump({'cwd': DATA_DIR}, f)

init_terminal_state()


# Get current working directory (shared for all users)
def get_cwd():
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
        return state['cwd']


# Set current working directory
def set_cwd(path):
    with open(STATE_FILE, 'w') as f:
        json.dump({'cwd': path}, f)



BLACKLIST_FILE = os.path.join(CONFIG_DIR, "blacklist.json")

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "w") as f:
            json.dump([], f)
        return []

    try:
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # If the file is empty or corrupted, reset it
        with open(BLACKLIST_FILE, "w") as f:
            json.dump([], f)
        return []

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(blacklist, f, indent=2)

def not_blacklisted():
    async def predicate(ctx):
        blacklist = load_blacklist()
        return str(ctx.author.id) not in blacklist
    return check(predicate)




# Ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)


CONFIG_FILE = os.path.join(CONFIG_DIR, 'file_permissions.json')
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({}, f)


# Now that dotenv is loaded, this will work
DC_TOKEN = os.getenv("DC_TOKEN")


if DC_TOKEN is None:
    raise ValueError("DC_TOKEN not found in .env file! Make sure your .env contains: DC_TOKEN=your_bot_token")


# Roles authorized to use mod commands
AUTHORIZED_ROLES = ["<Unpaid_Intern>", "<Admin>", "<Developer>", "<Head_Moderator>"]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents, help_command=None)

# Global debug toggle
debug_enabled = False

# -----------------------
# Error Manager
# -----------------------
ERROR_CODES = {
    1: "MemoryError: System ran out of memory",
    2: "SystemExit: Program is exiting",
    3: "KeyboardInterrupt: Execution interrupted by user",
    4: "SyntaxError: Invalid Python syntax",
    5: "NameError: Variable or file is not defined"
}

async def error_manager(ctx, code: int):
    """Send ANSI red error messages to Discord"""
    error_text = ERROR_CODES.get(code, "Unknown error code")
    ansi_message = f"```ansi\n\033[2;31mError: {error_text}\033[0m\n```"
    await ctx.send(ansi_message)

# -----------------------
# Role decorator
# -----------------------
def mod():
    """Decorator to allow only users with specific roles"""
    async def predicate(ctx):
        user_roles = [role.name for role in ctx.author.roles]
        return any(role in AUTHORIZED_ROLES for role in user_roles)
    return check(predicate)


def log_command(user: discord.Member, command: str, extra_info: str = ""):
    """
    Log a command usage.
    user: discord.Member who ran the command
    command: the command string (e.g., ">ls -a")
    extra_info: optional extra details
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(LOGS_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")

    log_entry = f"[{timestamp}] {user} ({user.id}) -> {command}"
    if extra_info:
        log_entry += f" | {extra_info}"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# -----------------------
# OS Initialization
# -----------------------
def os_init():
    """
    Deterministic OS initialization that auto-creates folders and config if missing.
    Returns:
      0 → Success
      1 → MemoryError
      2 → SystemExit (logs folder not writable)
    """
    required_folders = ["config", "data", "logs"]

    # Create folders if missing
    for folder in required_folders:
        path = os.path.join(BASE_DIR, folder)
        if not os.path.exists(path):
            os.makedirs(path)

    # Create default config file if missing
    config_file = os.path.join(BASE_DIR, "config", "settings.py")
    if not os.path.isfile(config_file):
        with open(config_file, "w") as f:
            f.write("# Default config\nBOOT = True\n")

    # Allocate memory for file/folder lists
    try:
        files = []
        folders = []
    except MemoryError:
        return 1

    # Ensure logs folder is writable
    logs_path = os.path.join(BASE_DIR, "logs")
    if not os.access(logs_path, os.W_OK):
        return 2

    return 0  # success

# -----------------------
# Events
# -----------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    if user_id in pending_inputs:
        varname, _ = pending_inputs.pop(user_id)
        value = message.content

        # Store the value in your variable system here
        # Example: set_variable(varname, value)
        await message.channel.send(f"Input stored as `{varname}`: `{value}`")
        log_command(message.author, f"input {varname} {value}", f"CWD: {get_cwd()}")

    await bot.process_commands(message)

# -----------------------
# Commands
# -----------------------





# Helper to load/save permissions
def load_permissions():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_permissions(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def get_user_dir(user_id):
    if user_id not in user_directories:
        user_directories[user_id] = DATA_DIR
        return user_directories[user_id]


def safe_path(base, target):
    final_path = os.path.abspath(os.path.join(base, target))
    if not final_path.startswith(os.path.abspath(DATA_DIR)):
        raise PermissionError("Access outside data folder is not allowed.")
        return final_path



# -----------------------
# Rename command
# -----------------------

import asyncio
import random
from discord.ext import commands

COMMANDS_ENABLED = True  # Make sure this is defined at the top

# --- Global command filter ---
@bot.check
async def check_commands_enabled(ctx):
    global COMMANDS_ENABLED
    # Always allow 'enable' and 'shutdown' even when disabled
    if ctx.command and ctx.command.name in ["enable", "shutdown"]:
        return True
    return COMMANDS_ENABLED

# --- Shutdown Command ---
@bot.command()
@mod()
async def shutdown(ctx):
    global COMMANDS_ENABLED
    await ctx.send("`Operating System Shutting Down`")
    await ctx.send("`Loading...`")
    await asyncio.sleep(random.randint(3, 5))
    COMMANDS_ENABLED = False
    await ctx.send("`System Shutdown Complete.`")




# Global check to block commands when disabled
@bot.check
async def check_commands_enabled(ctx):
    global COMMANDS_ENABLED
    return COMMANDS_ENABLED




@bot.command(name="rename")
@not_blacklisted()
async def rename(ctx, old_name: str, new_name: str):
    """
    Rename a file or folder in the current working directory.
    """
    cwd = Path(get_cwd())
    old_path = cwd / old_name
    new_path = cwd / new_name

    if not old_path.exists():
        await error_manager(ctx, 5)
        return

    if new_path.exists():
        await ctx.send(f"A file or folder named `{new_name}` already exists!")
        return

    try:
        old_path.rename(new_path)
        if echo_enabled:
            await ctx.send(f"`{old_name}` renamed to `{new_name}` successfully.")
        log_command(ctx.author, f"rename {old_name} {new_name}", f"CWD: {cwd}")
        

    except PermissionError:
        await error_manager(ctx, 2)
    except MemoryError:
        await error_manager(ctx, 1)


@bot.command(name="blacklist_add")
@mod()
async def blacklist_add(ctx, user_id: str):
    blacklist = load_blacklist()
    if user_id in blacklist:
        await ctx.send(f"User {user_id} is already blacklisted.")
        return
    blacklist.append(user_id)
    save_blacklist(blacklist)
    await ctx.send(f"User {user_id} added to blacklist.")

@bot.command(name="blacklist_remove")
@mod()
async def blacklist_remove(ctx, user_id: str):
    blacklist = load_blacklist()
    if user_id not in blacklist:
        await ctx.send(f"User {user_id} is not blacklisted.")
        return
    blacklist.remove(user_id)
    save_blacklist(blacklist)
    await ctx.send(f"User {user_id} removed from blacklist.")

@bot.command(name="blacklist_view")
@mod()
async def blacklist_view(ctx):
    blacklist = load_blacklist()
    if not blacklist:
        await ctx.send("Blacklist is empty.")
        return
    await ctx.send(f"Blacklisted users:\n{', '.join(blacklist)}")




import shlex

# ---------- helpers for recursive setting stored in STATE_FILE ----------
def get_state():
    """Return dict stored in STATE_FILE, ensure keys exist."""
    init_terminal_state()  # ensure file exists
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    # defaults
    if "recursive_allow" not in state:
        state["recursive_allow"] = False
    if "recursive_max_depth" not in state:
        state["recursive_max_depth"] = 2
    # persist defaults back if they were missing
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    return state

def set_state_value(key, value):
    init_terminal_state()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    state[key] = value
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ---------- parsing utility (respect quotes) ----------
def split_commands_and_separators(command_str: str):
    """
    Split a command string into segments separated by && or || while respecting quotes.
    Returns list of tuples: [(segment1, sep_after1), (segment2, sep_after2), ...]
    sep_after is '&&', '||' or None for the last segment.
    """
    tokens = shlex.split(command_str)
    segments = []
    current = []
    seps = []
    for tok in tokens:
        if tok in ("&&", "||"):
            segments.append((" ".join(current).strip(), tok))
            current = []
        else:
            current.append(tok)
    segments.append((" ".join(current).strip(), None))
    # filter out empty segments
    return [(seg, sep) for seg, sep in segments if seg != ""]

# -----------------------
# Recursive run settings
# -----------------------
RECURSIVE_ALLOW = False
MAX_RECURSION_DEPTH = 2

# Store user-defined variables
variables = {}


def get_variables():
    state = get_state()
    return state.setdefault("variables", {})

def set_variable(name, value):
    state = get_state()
    state["variables"][name] = value
    set_state_value("variables", state["variables"])


@bot.command(name="setvar")
@not_blacklisted()
async def setvar(ctx, name: str, *, value: str):
    variables[name] = value
    if echo_enabled:
        await ctx.send(f"Variable `{name}` set to `{value}`")
    log_command(ctx.author, f"setvar {name} {value}")


@bot.command(name="getvar")
@not_blacklisted()
async def getvar(ctx, name: str):
    """Get a variable value"""
    value = get_variables().get(name)
    if value is None:
        await ctx.send(f"Variable `${name}` does not exist")
    else:
        if echo_enabled:
            await ctx.send(f"`{name}` = `{value}`")

#input crap
@bot.command(name="input")
@not_blacklisted()
async def input_cmd(ctx, varname: str = None, *, display_message: str = None):
    """
    Prompt the user for input and store it under a variable name.
    
    Usage:
      >input (varname) "display message"
    """
    if varname is None or display_message is None:
        await ctx.send("Usage: >input (varname) \"display message\"")
        return

    # Strip parentheses from varname if present
    varname = varname.strip("()")

    # Store pending input
    pending_inputs[ctx.author.id] = (varname, display_message)
    await ctx.send(f"{display_message}")


# ---------- main runner with depth & && / || logic ----------

# -----------------------
# Pipe / sleep / echo commands
# -----------------------
@bot.command(name="echo")
@not_blacklisted()
async def echo(ctx, *, text: str):
    await ctx.send(text)
    log_command(ctx.author, f"echo {text}")

@bot.command(name="sleep")
@not_blacklisted()
async def sleep_cmd(ctx, seconds: float):
    import asyncio
    log_command(ctx.author, f"sleep {seconds}")
    await asyncio.sleep(seconds)
    if echo_enabled:
        await ctx.send(f"Slept for {seconds} seconds")


async def run_command_from_line(ctx, line):
    parts = shlex.split(line)
    if not parts:
        return True

    cmd_name = parts[0]
    args = parts[1:]

    # Handle built-in commands that expect positional args
    if cmd_name == "setvar":
        if len(args) < 2:
            await ctx.send("Usage: setvar <name> <value>")
            return False
        var_name = args[0]
        var_value = " ".join(args[1:])
        variables[var_name] = var_value
        await ctx.send(f"Variable `{var_name}` set to `{var_value}`")
        log_command(ctx.author, f"setvar {var_name} {var_value}")
        return True

    if cmd_name == "loop":
        if len(args) < 2:
            await ctx.send("Usage: loop <count> <command>")
            return False
        try:
            count = int(args[0])
        except ValueError:
            await ctx.send("Loop count must be a number.")
            return False
        nested_command = " ".join(args[1:])
        for _ in range(count):
            # Replace variables in the command
            for var_name, var_value in variables.items():
                nested_command = nested_command.replace(f"${var_name}", var_value)
            await run_commands(ctx, nested_command)
        if echo_enabled:    
            await ctx.send(f"Loop finished {count} iterations.")
        return True

    # fallback to normal invoke
    command_obj = bot.get_command(cmd_name)
    if command_obj:
        try:
            await ctx.invoke(command_obj, *args)
            return True
        except Exception as e:
            await ctx.send(f"`Command failed: {cmd_name} ({e})`")
            return False
    else:
        await ctx.send(f"`Unknown command: {cmd_name}`")
        return False


# -----------------------
# Source script command
# -----------------------
@bot.command(name="source")
@not_blacklisted()
async def source(ctx, filename: str):
    cwd = Path(get_cwd())
    file_path = cwd / filename
    log_command(ctx.author, f"source {filename}")

    if not str(file_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("You cannot source files outside the data folder!")
        return

    if not file_path.exists() or not file_path.is_file():
        await error_manager(ctx, 5)
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            await run_command_from_line(ctx, line)

    except Exception as e:
        await ctx.send(f"`Error running script: {e}`")



# -----------------------
# Enhanced run with recursion + pipes
# -----------------------
async def run_commands(ctx, command_str, depth=0):
    """
    Executes commands with support for:
      - && chaining
      - | pipes
      - recursive run up to MAX_RECURSION_DEPTH
    """
    if depth > MAX_RECURSION_DEPTH:
        await ctx.send("Max recursion depth reached!")
        return False

    commands_list = [cmd.strip() for cmd in command_str.split("&&")]
    for cmd_text in commands_list:
        if not cmd_text:
            continue

        # Check for pipes
        if "|" in cmd_text:
            parts = [p.strip() for p in cmd_text.split("|")]
            output = None
            for p_cmd in parts:
                # simulate sending previous output as arg
                if output:
                    p_cmd += f" {output}"
                result = await invoke_command(ctx, p_cmd, depth)
                if not result:
                    return False
                # capture last output (just for demonstration, echo only)
                output = p_cmd
        else:
            result = await invoke_command(ctx, cmd_text, depth)
            if not result:
                return False
    return True

async def invoke_command(ctx, cmd_text, depth):
    parts = shlex.split(cmd_text)  # respect quotes
    if not parts:
        return True

    cmd_name = parts[0]
    args = parts[1:]

    # Recursive  support
    if cmd_name == "run":
        state = get_state()
        if not state.get("recursive_allow", False) and depth > 0:
            await ctx.send("Recursive run is disabled!")
            return False
        nested_command = " ".join(args)
        return await run_commands(ctx, nested_command, depth + 1)

    command_obj = bot.get_command(cmd_name)
    if not command_obj:
        await ctx.send(f"`Unknown command: {cmd_name}`")
        return False

    try:
        # Check if command has a `*` parameter (VAR_KEYWORD / VAR_POSITIONAL)
        sig = command_obj.callback.__annotations__
        # If command expects a single string (like *, text)
        if any(param.kind.name == "VAR_POSITIONAL" or param.kind.name == "KEYWORD_ONLY"
               for param in command_obj.clean_params.values()):
            arg_string = " ".join(args)
            await ctx.invoke(command_obj, text=arg_string)  # pass as named parameter
        else:
            await ctx.invoke(command_obj, *args)
        return True
    except Exception as e:
        await ctx.send(f"`Command failed: {cmd_name} ({e})`")
        return False



# -----------------------
# Example utility commands
# -----------------------

@bot.command(name="@echo")
@not_blacklisted()
async def echo(ctx, *, state: str = None):
    """
    Toggle or set echo state. Usage:
    >echo off  → hides most command outputs
    >echo on   → shows outputs again
    >echo      → shows current state
    """
    global echo_enabled
    if state is None:
        await ctx.send(f"Echo is currently {'on' if echo_enabled else 'off'}.")
        return

    state = state.lower().strip()
    if state == "off":
        echo_enabled = False
        await ctx.send("Echo turned off.")
    elif state == "on":
        echo_enabled = True
        await ctx.send("Echo turned on.")
    else:
        await ctx.send("Usage: `>echo on` or `>echo off`.")


@bot.command(name="while")
@not_blacklisted()
async def while_cmd(ctx, variable: str, *, command_str: str):
    """
    Run a command repeatedly while a state variable is true.
    Usage:
    >while running echo "Still running"
    """
    state = get_state()
    log_command(ctx.author, f"while {variable} {command_str}")

    loop_count = 0
    while state.get(variable, True):  # default True if variable missing
        result = await run_commands(ctx, command_str, depth=0)
        if not result:
            await ctx.send(f"While loop stopped at iteration {loop_count+1} due to failure.")
            break
        loop_count += 1
        # Reload state each iteration
        state = get_state()



@bot.command(name="loop")
@not_blacklisted()
async def loop_cmd(ctx, count: int, *, command_str: str):
    for _ in range(count):
        # Replace variables in command
        cmd_with_vars = command_str
        for var_name, var_value in variables.items():
            cmd_with_vars = cmd_with_vars.replace(f"${var_name}", var_value)
        await run_commands(ctx, cmd_with_vars)
    if echo_enabled:    
        await ctx.send(f"Loop finished {count} iterations.")




@bot.command(name="cp")
@not_blacklisted()
async def cp(ctx, source: str, destination: str):
    from shutil import copy2, copytree
    cwd = Path(get_cwd())
    source_path = cwd / source
    destination_path = cwd / destination
    log_command(ctx.author, f"cp {source} {destination}")

    if not str(source_path.resolve()).startswith(str(Path(DATA_DIR).resolve())) or \
       not str(destination_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("Cannot copy outside root directory!")
        return

    if not source_path.exists():
        await error_manager(ctx, 5)
        return

    try:
        if source_path.is_dir():
            copytree(source_path, destination_path)
        else:
            copy2(source_path, destination_path)
        if echo_enabled:    
            await ctx.send(f"`{source}` copied to `{destination}` successfully.")
    except Exception as e:
        await ctx.send(f"`Copy failed: {e}`")



# ---------- top-level run command ----------
@bot.command(name="run")
@not_blacklisted()
async def run(ctx, *, commands_str: str):
    """
    Run multiple commands separated by && or ||.
    Supports nested `run` when enabled (max depth controlled in STATE_FILE).
    Example: >run mkfile \"my file.txt\" && ls && status
    """
    # top-level log
    log_command(ctx.author, f"run {commands_str}", f"CWD: {get_cwd()}")
    await run_commands(ctx, commands_str, depth=0)

# ---------- toggle command for recursive runs ----------
@bot.command(name="set_recursive_allow")
@mod()  # you can change this to allow anyone; default mod-only is safer
@not_blacklisted()
async def set_recursive_allow(ctx, value: str):
    """
    Enable or disable nested `run` support.
    Usage: >set_recursive_allow true  OR  >set_recursive_allow false
    """
    val = value.strip().lower()
    if val in ("1", "true", "yes", "on"):
        set_state_value("recursive_allow", True)
        await ctx.send("Recursive `run` enabled (max depth = 2).")
    elif val in ("0", "false", "no", "off"):
        set_state_value("recursive_allow", False)
        await ctx.send("Recursive `run` disabled.")
    else:
        await ctx.send("Invalid value. Use `true` or `false`.")

# optional: command to view current recursive settings
@bot.command(name="view_recursive_setting")
@mod()
@not_blacklisted()
async def view_recursive_setting(ctx):
    s = get_state()
    await ctx.send(f"recursive_allow = {s.get('recursive_allow')}  max_depth = {s.get('recursive_max_depth')}")





# -----------------------
# Move (mv) command
# -----------------------
@bot.command(name="mv")
@not_blacklisted()
async def mv(ctx, source: str, destination: str):
    """
    Move a file or folder from current working directory to another folder (can also rename while moving).
    """
    cwd = Path(get_cwd())
    source_path = (cwd / source).resolve()
    destination_path = (cwd / destination).resolve()

    # Prevent moving outside of DATA_DIR
    if not str(source_path).startswith(str(Path(DATA_DIR).resolve())) or \
       not str(destination_path).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("Cannot move files outside the root directory!")
        return

    if not source_path.exists():
        await error_manager(ctx, 5)
        return

    if destination_path.exists():
        await ctx.send("Destination already exists!")
        return

    try:
        # Ensure the parent folder exists
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        source_path.rename(destination_path)
        if echo_enabled:
            await ctx.send(f"`{source}` moved to `{destination}` successfully.")
        log_command(ctx.author, f"mv {source} {destination}", f"CWD: {cwd}")

    except PermissionError:
        await error_manager(ctx, 2)
    except MemoryError:
        await error_manager(ctx, 1)




@bot.command(name='cd')
@not_blacklisted()
# Change directory command
async def cd(ctx, directory: str):
    log_command(ctx.author, f"cd {' '.join(directory)}") #log stuff idk
    cwd = get_cwd()
    new_path = os.path.join(cwd, directory)
    new_path = os.path.abspath(new_path)


    # Prevent leaving the root DATA_DIR
    if not new_path.startswith(DATA_DIR):
        await ctx.send(f"`Cannot leave root directory C:/root`")
        return


    if os.path.isdir(new_path):
        set_cwd(new_path)
        display_path = 'C:/root' + new_path[len(DATA_DIR):].replace('\\', '/')
        if echo_enabled:
            await ctx.send(f"`Directory changed to `{display_path}``")
    else:
        await ctx.send(f"`Directory does not exist: {directory}`")


@bot.command(name='mkdir')
@not_blacklisted()
async def mkdir(ctx, folder_name: str):
    log_command(ctx.author, f"mkdir {' '.join(folder_name)}")
    cwd = get_cwd()
    new_folder = os.path.join(cwd, folder_name)
    if not new_folder.startswith(DATA_DIR):
        await ctx.send(f"`Cannot create folder outside root`")
        return


    os.makedirs(new_folder, exist_ok=True)
    display_path = 'C:/root' + new_folder[len(DATA_DIR):].replace('\\', '/')
    if echo_enabled:
        await ctx.send(f"Folder created: `{display_path}`")

    # File password and permission system
@bot.command(name="setpass")
@not_blacklisted()
async def setpass(ctx, filename: str, password: str):
    log_command(ctx.author, f"setpass {' '.join(filename)} {''.join(password)}")
    perms = load_permissions()
    perms.setdefault(filename, {})['password'] = password
    save_permissions(perms)
    await ctx.send(f"Password set for `{filename}`.")



@bot.command(name="status")
@not_blacklisted()
async def status(ctx):
    await ctx.send("If I'm talking then TS is on DUH")

@bot.command(name="debug")
@not_blacklisted()
async def debug(ctx):
    await ctx.send("Debug not active because I have NOTHING TO debug")

@bot.command(name="os_boot")
@mod()
@not_blacklisted()
async def os_boot(ctx):
    log_command(ctx.author, f"os_boot")
    code = os_init()
    if code == 0:
        await ctx.send("`OS initialized successfully! All folders and config are ready.`")
    else:
        await error_manager(ctx, code)

from datetime import datetime








@bot.command(name="edit")
@not_blacklisted()
async def edit(ctx, action: str, filename: str, *, content: str = None):
    """
    File editor sandboxed to the 'data' folder.
    
    Usage:
    >edit read <filename>          → Read a file
    >edit write <filename> <text> → Overwrite a file
    >edit append <filename> <text>→ Append to a file
    """

    cwd = Path(get_cwd())  # Get current working directory
    file_path = cwd / filename

    # Prevent directory traversal outside DATA_DIR
    if not str(file_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("You cannot access files outside the data folder!")
        return

    try:
        if action.lower() == "read":
            if not file_path.is_file():
                await error_manager(ctx, 5)  # File not found
                return

            with open(file_path, "r", encoding="utf-8") as f:
                data = f.read()

            if not data:
                data = "(File is empty)"
            await ctx.send(f"```txt\n{data}\n```")
            log_command(ctx.author, f"edit read {filename}", f"CWD: {cwd}")

        elif action.lower() == "write":
            if content is None:
                await ctx.send("You must provide content to write.")
                return

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if echo_enabled:
                await ctx.send(f"File `{filename}` overwritten successfully at `C:/root/{file_path.relative_to(DATA_DIR).as_posix()}`.")
            log_command(ctx.author, f"edit write {filename} {content}", f"CWD: {cwd}")

        elif action.lower() == "append":
            if content is None:
                await ctx.send("You must provide content to append.")
                return

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
            if echo_enabled:
                await ctx.send(f"Content appended to `{filename}` successfully at `C:/root/{file_path.relative_to(DATA_DIR).as_posix()}`.")
            log_command(ctx.author, f"edit append {filename} {content}", f"CWD: {cwd}")

        else:
            await ctx.send("Invalid action! Use `read`, `write`, or `append`.")

    except PermissionError:
        await error_manager(ctx, 2)  # SystemExit for unwritable file
    except MemoryError:
        await error_manager(ctx, 1)


from pathlib import Path

# -----------------------
# List directory with tree view
# -----------------------
@bot.command(name="ls")
@not_blacklisted()
async def ls(ctx, *flags):
    log_command(ctx.author, f"ls {' '.join(flags)}")
    cwd = Path(get_cwd())
    show_hidden = '-a' in flags

    def tree(path: Path, prefix=''):
        items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        lines = []
        for i, item in enumerate(items):
            if not show_hidden and item.name.startswith('.'):
                continue

            connector = '└─ ' if i == len(items) - 1 else '├─ '
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                extension = '  ' if i == len(items) - 1 else '│ '
                lines.extend(tree(item, prefix + extension))
            else:
                lines.append(f"{prefix}{connector}{item.name}")
        return lines

    try:
        if not cwd.exists():
            await error_manager(ctx, 5)
            return

        output_lines = tree(cwd)
        if not output_lines:
            output_lines = ['(Empty folder)']

        await ctx.send(f"```\nC:/root/{cwd.relative_to(DATA_DIR).as_posix()}\n" +
                       '\n'.join(output_lines) + "\n```")
    except PermissionError:
        await error_manager(ctx, 2)


# -----------------------
# Create a file
# -----------------------
@bot.command(name="mkfile")
@not_blacklisted()
async def mkfile(ctx, filename: str):
    log_command(ctx.author, f"mkfile {' '.join(filename)}")
    cwd = Path(get_cwd())
    file_path = cwd / filename

    # Prevent directory traversal
    if not str(file_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("You cannot create files outside the data folder!")
        return

    try:
        if file_path.exists():
            await ctx.send(f"File `{filename}` already exists.")
            return

        # Create an empty file
        file_path.touch(exist_ok=False)
        if echo_enabled:
            await ctx.send(f"File `{filename}` created successfully at `C:/root/{file_path.relative_to(DATA_DIR).as_posix()}`.")
    except PermissionError:
        await error_manager(ctx, 2)
    except MemoryError:
        await error_manager(ctx, 1)






# -----------------------
# Delete a file
# -----------------------
@bot.command(name="rmfile")
@not_blacklisted()
async def rmfile(ctx, filename: str):
    log_command(ctx.author, f"rmfile {' '.join(filename)}")
    """
    Delete a file in the current working directory.
    """
    cwd = Path(get_cwd())
    file_path = cwd / filename

    # Prevent directory traversal outside DATA_DIR
    if not str(file_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("You cannot delete files outside the data folder!")
        return

    try:
        if not file_path.is_file():
            await error_manager(ctx, 5)  # File not found
            return

        file_path.unlink()  # Delete file
        if echo_enabled:
            await ctx.send(f"File `{filename}` deleted successfully at `C:/root/{file_path.relative_to(DATA_DIR).as_posix()}`.")
    except PermissionError:
        await error_manager(ctx, 2)
    except MemoryError:
        await error_manager(ctx, 1)


from pathlib import Path

@bot.command(name="rmdir")
@not_blacklisted()
async def rmdir(ctx, folder_name: str):
    """
    Remove a directory inside the working directory.
    """
    cwd = Path(get_cwd())
    folder_path = cwd / folder_name

    # Prevent deleting outside of DATA_DIR
    if not str(folder_path.resolve()).startswith(str(Path(DATA_DIR).resolve())):
        await ctx.send("You cannot remove folders outside the root directory!")
        return

    try:
        if not folder_path.exists() or not folder_path.is_dir():
            await error_manager(ctx, 5)  # NameError for missing folder
            return

        # Only remove empty folders for safety
        if any(folder_path.iterdir()):
            await ctx.send(f"Folder `{folder_name}` is not empty! Use `rmdir` on empty folders only.")
            return

        folder_path.rmdir()
        if echo_enabled:
            await ctx.send(f"Folder `{folder_name}` removed successfully.")
        
        # Log the deletion
        log_command(ctx.author, f"rmdir {folder_name}", f"CWD: {cwd}")

    except PermissionError:
        await error_manager(ctx, 2)
    except MemoryError:
        await error_manager(ctx, 1)




@bot.command(name="help")

async def help_cmd(ctx, topic: str = None):
    """
    Show a full list of commands and descriptions.
    Usage:
      >help             → shows all commands
      >help <command>   → shows details for a specific command
    """
    log_command(ctx.author, f"help {topic if topic else ''}")

    commands_info = {
        "ls": "List files/folders in the current directory. Flags: -a, -l, -h, -r, -t, -R",
        "cd": "Change the current working directory.",
        "mkdir": "Create a new folder in the current directory.",
        "rmdir": "Remove an empty folder in the current directory.",
        "mkfile": "Create a new empty file (must be .exe if sourcing).",
        "rmfile": "Delete a file in the current directory.",
        "edit": "Read, write, or append to a file. Usage: >edit <read/write/append> <filename> [content]",
        "rename": "Rename a file or folder.",
        "mv": "Move a file/folder to another location.",
        "cp": "Copy a file or folder to another location.",
        "source": "Run commands from a .exe file script. Supports loops and variables.",
        "run": "Run one or more commands separated by &&. Supports nested loops if enabled.",
        "set_recursive_allow": "Enable or disable nested `run` support. Usage: true/false",
        "view_recursive_setting": "View current recursive run settings (allow + max depth).",
        "echo": "Print text to the terminal.",
        "sleep": "Pause execution for a number of seconds.",
        "setvar": "Set a variable for scripts: >setvar name value",
        "getvar": "Get a variable value: >getvar name",
        "status": "Check if the terminal is active.",
        "debug": "Debug information (currently placeholder).",
        "os_boot": "Initialize the OS and check all folders/configs.",
        "help": "Show this help message, or help for a specific command.",
        "test_error": "Simulate an error code for testing (mod only)."
    }

    if topic is None:
        # Full list
        help_text = "\n".join(f"{cmd:20} → {desc}" for cmd, desc in commands_info.items())
        await ctx.send(f"```ansi\n\033[2;34m{help_text}\033[0m\n```")  # Blue text
    else:
        topic_lower = topic.lower()
        if topic_lower in commands_info:
            await ctx.send(f"```ansi\n\033[2;33m{topic_lower} → {commands_info[topic_lower]}\033[0m\n```")  # Yellow text
        else:
            await ctx.send(f"No help available for `{topic}`")




@bot.command(name="test_error")
@mod()
@not_blacklisted()
async def test_error(ctx, code: int):
    """Simulate sending an error code"""
    await error_manager(ctx, code)

# -----------------------
# Run bot
# -----------------------
bot.run(DC_TOKEN)
