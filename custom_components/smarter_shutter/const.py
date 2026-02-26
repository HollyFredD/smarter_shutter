"""Constants for Smarter Shutter."""

DOMAIN = "smarter_shutter"

# Control modes
MODE_SWITCHES = "switches"
MODE_COVER = "cover"

# Config keys
CONF_CONTROL_MODE = "control_mode"
CONF_OPEN_SWITCH = "open_switch_entity_id"
CONF_CLOSE_SWITCH = "close_switch_entity_id"
CONF_COVER_ENTITY = "cover_entity_id"
CONF_TRAVEL_TIME_UP = "travel_time_up"
CONF_TRAVEL_TIME_DOWN = "travel_time_down"
CONF_MOTOR_INERTIA = "motor_inertia"

# Stop methods
CONF_STOP_METHOD = "stop_method"
STOP_METHOD_STOP = "stop_command"
STOP_METHOD_RESEND = "resend_direction"
DEFAULT_STOP_METHOD = STOP_METHOD_STOP

# Defaults
DEFAULT_TRAVEL_TIME = 30
DEFAULT_MOTOR_INERTIA = 0.3

# Directions
DIR_UP = "up"
DIR_DOWN = "down"
