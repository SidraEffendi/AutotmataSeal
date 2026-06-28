import json
import os
from datetime import datetime
from typing import Any, Dict

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "finance_data.json")

DEFAULT_DATA: Dict[str, Any] = {
    "transactions": [],
    "budget_limits": {},
    "goals": [],
    "debts": [],
    "risk_profile": None,
}


def load() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in DEFAULT_DATA.items()}
    with open(DATA_FILE) as f:
        data = json.load(f)
    for key, val in DEFAULT_DATA.items():
        if key not in data:
            data[key] = val.copy() if isinstance(val, (dict, list)) else val
    return data


def save(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)
