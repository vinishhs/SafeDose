import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(filename: str) -> Dict[str, Any]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{filename} must contain a JSON object")
    return data


@lru_cache(maxsize=1)
def load_interactions() -> Dict[str, Any]:
    return _load_json("interactions.json")


@lru_cache(maxsize=1)
def load_dosage_rules() -> Dict[str, Any]:
    return _load_json("dosage_rules.json")


@lru_cache(maxsize=1)
def load_alternatives() -> Dict[str, Any]:
    return _load_json("alternatives.json")


@lru_cache(maxsize=1)
def load_allergy_map() -> Dict[str, Any]:
    return _load_json("allergy_map.json")
