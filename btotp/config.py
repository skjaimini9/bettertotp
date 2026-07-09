import os
import json

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "btotp")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "time_step": 45,
    "code_length": 12,
    "hash_algo": "sha512",
    "clipboard": False,
}


def load_config() -> dict:
    config = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                user_config = json.load(f)
            config.update(user_config)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(updates: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = load_config()
    config.update(updates)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
