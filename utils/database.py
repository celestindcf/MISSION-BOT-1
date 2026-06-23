import json
import os
from datetime import datetime

DATA_FILE = "data/missions.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"missions": [], "agents": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)

def create_mission(title, description, assigned_to=None, priority="moyenne"):
    data = load_data()
    mission = {
        "id": len(data["missions"]) + 1,
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "priority": priority,
        "status": "en attente",  # en attente, en cours, terminée, annulée
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    data["missions"].append(mission)
    save_data(data)
    return mission

def update_mission_status(mission_id, status):
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["status"] = status
            m["updated_at"] = datetime.now().isoformat()
            save_data(data)
            return True
    return False

def assign_mission(mission_id, agent_id):
    data = load_data()
    for m in data["missions"]:
        if m["id"] == mission_id:
            m["assigned_to"] = agent_id
            m["status"] = "en cours"
            m["updated_at"] = datetime.now().isoformat()
            save_data(data)
            return True
    return False

def get_missions_by_agent(agent_id):
    data = load_data()
    return [m for m in data["missions"] if m["assigned_to"] == agent_id]

def get_all_missions():
    data = load_data()
    return data["missions"]
