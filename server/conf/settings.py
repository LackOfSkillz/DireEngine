r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "dragonsire"

BASE_ACCOUNT_TYPECLASS = "typeclasses.accounts.Account"
BASE_GUEST_TYPECLASS = "typeclasses.accounts.Guest"
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.Character"
AT_SERVER_STARTSTOP_MODULE = "server.conf.at_server_startstop"
DEFAULT_HOME = "#2"
COMMAND_PARSER = "server.conf.cmdparser.cmdparser"
SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"
SERVER_SESSION_CLASS = "server.conf.serversession.ServerSession"
TELNET_PROTOCOL_CLASS = "server.conf.telnet.NoMCCPTelnetProtocol"
TELNET_INTERFACES = ["127.0.0.1", "::1"]
WEBSERVER_INTERFACES = ["127.0.0.1"]
WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
MAX_NR_CHARACTERS = 5
ENABLE_GLOBAL_STATUS_TICK = True
ENABLE_GUARD_SYSTEM = True
ENABLE_PER_GUARD_GUARD_BEHAVIOR = False
ENABLE_DIRESIM_KERNEL = True
ENABLE_LEGACY_GUARD_TEST_ADAPTER = False
STRICT_DIRESIM_LEGACY_GUARD_SEAL = False
ENABLE_LEGACY_GUARD_TRIPWIRE = True
ENABLE_DIRESIM_DECISION_LOGGING = True
DIRESIM_COMMIT_MODE = "full"
MAX_ACTIVE_GUARDS = 3
MAX_EVENT_WAKE_NPCS = 10
GUARD_PATROL_OWNER = "reactor"
GUARD_PATROL_MODE = "hybrid"
ENABLE_GUARD_PATROL_DEBUG = False
GUARD_TICK_WARN_SECONDS = 0.10
ENABLE_GUARD_BEHAVIOR_TIMING = True
GUARD_BEHAVIOR_WARN_SECONDS = 0.05
GUARD_PER_GUARD_INTERVAL = 25.0
GUARD_PER_GUARD_JITTER = 5.0
GUARD_PER_GUARD_ROLLOUT_COUNT = 0
ENABLE_GUARD_SCRIPT_DIAGNOSTICS = True
GUARD_SCRIPT_DIAGNOSTIC_GUARD_ID = 0
GUARD_SCRIPT_FORCE_MOVE_DIAGNOSTIC = True
ENABLE_GUARD_STARTUP_TRACE = True
ENABLE_GUARD_STARTUP_FORCE_SYNC_DIAGNOSTIC = True
ENABLE_SERVER_STARTUP_BOOTSTRAP = False
ENABLE_SERVER_STARTUP_HOOKS = True
STATUS_TICK_WARN_SECONDS = 0.25
LEARNING_TICK_WARN_SECONDS = 0.25
SERVER_LOG_MAX_SIZE = 50_000_000
PORTAL_LOG_MAX_SIZE = 50_000_000
PORTAL_SERVICES_PLUGIN_MODULES.append("evennia.contrib.base_systems.godotwebsocket.webclient")
GODOT_CLIENT_WEBSOCKET_PORT = 4008
GODOT_CLIENT_WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
LLM_ENABLED = False
LLM_BASE_URL = "http://192.168.200.246:1234"
LLM_MODEL = "mistral-nemo-12b-instruct"
LLM_TIMEOUT = 60.0
LLM_TEMPERATURE = 0.5
LOG_LLM_CALLS = True


######################################################################
# Game-time calendar
######################################################################
# Game time runs at TIME_FACTOR x real time. With 4.0, four game days
# pass per one real-world day, giving a single 6-hour real-world play
# session a full day/night cycle in-game.
TIME_FACTOR = 4.0
# Game time pauses while the server is offline. This keeps time-of-day
# continuous across reloads from the player's perspective. Season is
# anchored separately to real-world wall-clock time so it does not
# drift during outages.
TIME_IGNORE_DOWNTIMES = False
# Real-world timezone used to compute the current season. Festivals
# and seasonal content align with this timezone's calendar months.
CALENDAR_TIMEZONE = "America/New_York"


######################################################################
# Weather system
######################################################################
# How often the weather progression evaluates each zone.
# Expressed in game-seconds for public-state reporting compatibility.
# State progression cadence is derived internally from the
# atmospheric interval and the state-tick ratio below.
WEATHER_TICK_INTERVAL_GAME_SECONDS = 900

# MT-514b-ambient: fast rhythm for ambient weather broadcasts.
# Default 240 seconds = 4 real minutes between atmospheric ticks.
WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS = 240

# State progression fires every Nth atmospheric tick.
# Default 5 means weather state progression every 20 real minutes.
WEATHER_STATE_TICK_RATIO = 5

# Chance an atmospheric tick broadcasts an ambient message for a
# holding weather state. Keeps weather lively without message spam.
WEATHER_AMBIENT_BROADCAST_PROBABILITY = 0.4

# MT-514b-perf-v4 mitigation: temporarily disable automatic weather
# ticks while production cycle time exceeds acceptable bounds.
# This flag is read by WeatherScript.at_repeat(). When False, the
# script's repeat callback returns early without running the cycle.
# Set to True (or remove the setting) only after live cycle time
# is verified under 2 seconds in production.
WEATHER_AUTOTICK_ENABLED = True

# Probability per tick that a zone in `storm` state produces a
# lightning/thunder atmospheric event. Tick is 15 game-minutes,
# so probability of ~0.5 means roughly one event per 30 game-minutes
# of storm.
WEATHER_LIGHTNING_PROBABILITY_PER_TICK = 0.5


######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
