# src/stagerun_compiler/backend.py
import json
import os
from typing import Dict, Any

def emit_json(ir: Dict[str, Any], out_path: str) -> str:
    """
    Write IR dictionary as pretty JSON to out_path.
    Creates parent dirs if necessary.
    Returns out_path.
    """
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ir, f, indent=2, ensure_ascii=False)
    return out_path
