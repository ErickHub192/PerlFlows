# app/models/clarify_models.py
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class ClarifyPayload:
    clarifyAnswers: Dict[str, Any]
    node_ids: List[str]
