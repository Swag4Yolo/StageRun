"""
serializer.py
---------------------------------------
Handles serialization and deserialization of ProgramNode objects
with integrity verification using SHA-256 checksums.

Format of serialized file:
    <sha256sum>\n<binary pickle-serialized object>

Usage:
    from Core.serializer import save_program, load_program
"""

import pickle
import hashlib
from pathlib import Path
from typing import Any


# ============================================================
# Core serialization
# ============================================================

def _compute_checksum(data: bytes) -> str:
    """Compute SHA256 checksum (hex) for given binary data."""
    return hashlib.sha256(data).hexdigest()


def save_program(program_node: Any, output_path: str | Path) -> str:
    """
    Serialize a ProgramNode object to a file with checksum protection.

    The output file will contain:
        <sha256 checksum>\n<pickle-serialized object>

    Returns the checksum string.
    """
    output_path = Path(output_path)
    data = pickle.dumps(program_node, protocol=pickle.HIGHEST_PROTOCOL)
    checksum = _compute_checksum(data)

    with output_path.open("wb") as f:
        f.write(checksum.encode("utf-8") + b"\n" + data)

    return checksum


def load_program(input_path: str | Path, expected_type: type | None = None) -> Any:
    """
    Load and verify a serialized ProgramNode from disk.

    - Verifies SHA256 checksum integrity.
    - Optionally ensures the object type matches `expected_type`.

    Raises:
        ValueError if checksum mismatch or wrong type.
    """
    input_path = Path(input_path)

    with input_path.open("rb") as f:
        stored_checksum = f.readline().strip().decode("utf-8")
        data = f.read()

    computed_checksum = _compute_checksum(data)
    if stored_checksum != computed_checksum:
        raise ValueError(
            f"Checksum mismatch for {input_path.name}! "
            f"(expected {stored_checksum}, got {computed_checksum})"
        )

    obj = pickle.loads(data)

    if expected_type is not None and not isinstance(obj, expected_type):
        raise ValueError(
            f"Deserialized object is not of expected type {expected_type.__name__}. "
            f"Got {type(obj).__name__}."
        )

    return obj


# ============================================================
# CLI helpers (optional)
# ============================================================

def verify_checksum(file_path: str | Path) -> bool:
    """
    Verify the checksum of a serialized file without loading the object.
    Returns True if the checksum matches, False otherwise.
    """
    file_path = Path(file_path)

    with file_path.open("rb") as f:
        stored_checksum = f.readline().strip().decode("utf-8")
        data = f.read()

    return stored_checksum == _compute_checksum(data)