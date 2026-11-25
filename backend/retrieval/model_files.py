"""Verify local embedding assets before opening the model (C15)."""

import tomllib
from hashlib import file_digest
from pathlib import Path

_FORBIDDEN = {".bin", ".pt", ".pkl", ".ckpt"}


def verify_embedding_files(model_dir: Path, manifest: Path) -> Path:
    with manifest.open("rb") as source:
        files = tomllib.load(source)["embedding"]["files"]
    if "model.safetensors" not in files:
        raise ValueError("Embedding manifest must pin safetensors weights")
    if any(path.suffix.lower() in _FORBIDDEN for path in model_dir.rglob("*")):
        raise ValueError("Unsupported weight format in embedding directory")
    for name, expected in files.items():
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Invalid embedding asset name")
        path = model_dir / name
        if path.is_symlink():
            raise ValueError(f"Embedding asset is a symlink: {name}")
        with path.open("rb") as asset:
            actual = file_digest(asset, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Embedding checksum mismatch: {name}")
    return model_dir
