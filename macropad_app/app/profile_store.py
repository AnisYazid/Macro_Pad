"""
profile_store.py
-----------------
Persists Profile objects to JSON files in a per-user app data folder, and
ships a set of sensible built-in starter profiles (Gaming / OBS / General).
"""

import json
import os
from pathlib import Path
from typing import List

from .protocol import Profile


def _app_data_dir() -> Path:
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home))
    else:
        base = home / ".config"
    d = base / "NissouMacroPad" / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_profile_names() -> List[str]:
    d = _app_data_dir()
    names = sorted(p.stem for p in d.glob("*.json"))
    if not names:
        save_profile(Profile(name="Custom"))
        names = sorted(p.stem for p in d.glob("*.json"))
    return names


def save_profile(profile: Profile):
    d = _app_data_dir()
    path = d / f"{profile.name}.json"
    path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")


def load_profile(name: str) -> Profile:
    d = _app_data_dir()
    path = d / f"{name}.json"
    if not path.exists():
        return Profile(name=name)
    data = json.loads(path.read_text(encoding="utf-8"))
    return Profile.from_dict(data)


def delete_profile(name: str):
    d = _app_data_dir()
    path = d / f"{name}.json"
    if path.exists():
        path.unlink()


def default_profiles() -> List[Profile]:
    gaming = Profile(name="Gaming", sensitivity=3)
    gaming.keys = {1: "W", 2: "A", 3: "S", 4: "D", 5: "R", 6: "E", 7: "TAB", 8: "SHIFT", 9: "SPACE"}
    gaming.encoder = {
        "CW": "VOLUME_UP", "CCW": "VOLUME_DOWN", "DOUBLE_PRESS": "",
    }

    obs = Profile(name="OBS Streaming", sensitivity=3)
    obs.keys = {
        1: "CTRL+SHIFT+R", 2: "CTRL+SHIFT+S", 3: "CTRL+SHIFT+M",
        4: "F9", 5: "F10", 6: "F11",
        7: "", 8: "", 9: "",
    }
    obs.encoder = {
        "CW": "VOLUME_UP", "CCW": "VOLUME_DOWN", "DOUBLE_PRESS": "",
    }

    general = Profile(name="General", sensitivity=3)
    general.keys = {
        1: "CTRL+C", 2: "CTRL+V", 3: "CTRL+Z",
        4: "F1", 5: "F2", 6: "F3",
        7: "MEDIA_PLAY_PAUSE", 8: "MEDIA_MUTE", 9: "ALT+TAB",
    }
    general.encoder = {
        "CW": "VOLUME_UP", "CCW": "VOLUME_DOWN", "DOUBLE_PRESS": "MEDIA_PLAY_PAUSE",
    }

    return [gaming, obs, general]
