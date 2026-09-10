"""
protocol.py
-----------
Defines the plain-text line protocol used to configure the macro pad
over a USB CDC serial connection (Option B from the design doc:
ESP32-S3 exposes a HID keyboard endpoint *and* a config/serial endpoint).

Each command is a single line, comma-separated, terminated with '\n'.
The firmware is expected to reply with "OK" or "ERR,<reason>".

    SET_KEY,<index 1-9>,<key_combo>
    SET_ENCODER,<CW|CCW|DOUBLE_PRESS>,<action>
    SET_SENSITIVITY,<int 1-40>
    SET_PROFILE_NAME,<name>
    SAVE
    LOAD
    PING
    GET_INFO
"""

from dataclasses import dataclass, field
from typing import Dict


# Encoder event types the firmware understands
ENCODER_EVENTS = [
    "CW",
    "CCW",
    "DOUBLE_PRESS",
]

SENSITIVITY_MIN = 0
SENSITIVITY_MAX = 10


@dataclass
class Profile:
    """A single macro pad configuration profile."""
    name: str = "Default"
    app_match: str = ""
    # key index (1-9) -> key combo string, e.g. "CTRL+C"
    keys: Dict[int, str] = field(default_factory=lambda: {i: "" for i in range(1, 10)})
    # encoder event -> action string, e.g. "VOLUME_UP"
    encoder: Dict[str, str] = field(default_factory=lambda: {e: "" for e in ENCODER_EVENTS})
    sensitivity: int = 3

    def to_dict(self):
        return {
            "name": self.name,
            "app_match": self.app_match,
            "keys": {str(k): v for k, v in self.keys.items()},
            "encoder": dict(self.encoder),
            "sensitivity": self.sensitivity,
        }

    @staticmethod
    def from_dict(d):
        p = Profile(name=d.get("name", "Default"), app_match=d.get("app_match", ""))
        p.keys = {int(k): v for k, v in d.get("keys", {}).items()}
        for i in range(1, 10):
            p.keys.setdefault(i, "")
        p.encoder = {e: d.get("encoder", {}).get(e, "") for e in ENCODER_EVENTS}
        p.sensitivity = int(d.get("sensitivity", 3))
        return p


def build_key_command(index: int, combo: str) -> str:
    value = combo if combo else "NONE"
    if value != "NONE" and not value.startswith("TEXT:") and "+" not in value and value.upper() not in {
        "CTRL", "SHIFT", "ALT", "GUI", "WIN", "CMD", "ENTER", "RETURN",
        "TAB", "ESC", "SPACE", "BACKSPACE", "DELETE", "INSERT", "HOME", "END",
        "LEFT", "RIGHT", "UP", "DOWN", "PAGEUP", "PAGEDOWN", "CAPSLOCK",
        "NUMLOCK", "SCROLLLOCK", "PAUSE", "MENU", "PLUS", "PRTSC",
        *(f"F{i}" for i in range(1, 25)),
    }:
        value = f"TEXT:{value}"
    return f"SET_KEY,{index},{value}"


def build_encoder_command(event: str, action: str) -> str:
    return f"SET_ENCODER,{event},{action if action else 'NONE'}"


def build_sensitivity_command(value: int) -> str:
    value = max(SENSITIVITY_MIN, min(SENSITIVITY_MAX, value))
    return f"SET_SENSITIVITY,{value}"


def build_profile_name_command(name: str) -> str:
    safe = name.replace(",", " ")
    return f"SET_PROFILE_NAME,{safe}"


def commands_for_profile(profile: Profile, include_save: bool = True):
    """Yield every command needed to push a full profile to the device."""
    yield build_profile_name_command(profile.name)
    for idx in range(1, 10):
        yield build_key_command(idx, profile.keys.get(idx, ""))
    for event in ENCODER_EVENTS:
        yield build_encoder_command(event, profile.encoder.get(event, ""))
    yield build_sensitivity_command(profile.sensitivity)
    if include_save:
        yield "SAVE"
