import os
import json

CONFIG_FILE = "config.json"
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")
OWNER_ID = 1239559463090917407  # Remplace par ton ID Discord

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "roles": {
                "commandant": {
                    "name": "Commandant",
                    "id": None,
                    "permissions": ["assign", "unassign", "status", "priority", "missions", "agents", "agent_info", "config_show", "role_rename", "role_link", "user_override", "user_remove", "perms_list"]
                },
                "capitaine": {
                    "name": "Capitaine",
                    "id": None,
                    "permissions": ["assign", "status", "missions", "agents"]
                },
                "agent": {
                    "name": "Agent",
                    "id": None,
                    "permissions": ["my_missions", "complete"]
                },
                "stagiaire": {
                    "name": "Stagiaire",
                    "id": None,
                    "permissions": ["my_missions"]
                }
            },
            "overrides": {},
            "log_channel": None
        }
        save_config(default)
        return default
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)
