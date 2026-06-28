import copy
import json
import os
from typing import Any, Dict, Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "finance_data.json")

DEFAULT_DATA: Dict[str, Any] = {
    "transactions": [],
    "budget_limits": {},
    "goals": [],
    "debts": [],
    "risk_profile": None,
}

# When set, all reads/writes go to memory instead of disk (used by web API)
_session: Optional[Dict[str, Any]] = None


def init_session(data: Optional[Dict[str, Any]] = None) -> None:
    global _session
    if data:
        _session = copy.deepcopy(data)
        for key, val in DEFAULT_DATA.items():
            if key not in _session:
                _session[key] = copy.deepcopy(val)
    else:
        _session = copy.deepcopy(DEFAULT_DATA)


def get_session() -> Optional[Dict[str, Any]]:
    return copy.deepcopy(_session) if _session is not None else None


def clear_session() -> None:
    global _session
    _session = None


def load() -> Dict[str, Any]:
    if _session is not None:
        return copy.deepcopy(_session)
    if not os.path.exists(DATA_FILE):
        return copy.deepcopy(DEFAULT_DATA)
    with open(DATA_FILE) as f:
        data = json.load(f)
    for key, val in DEFAULT_DATA.items():
        if key not in data:
            data[key] = copy.deepcopy(val)
    return data


def save(data: Dict[str, Any]) -> None:
    global _session
    if _session is not None:
        _session = data
        return
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)
