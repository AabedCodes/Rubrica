"""Stage only hash-pinned embedding files during the image build."""

import sys
import tomllib
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

MODEL = "https://huggingface.co/BAAI/bge-small-en-v1.5"
FILES = {
    "model.safetensors",
    "config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
}


def stage(manifest: Path, output: Path) -> None:
    with manifest.open("rb") as source:
        pin = tomllib.load(source)["embedding"]
    revision = pin["revision"]
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("Invalid embedding revision")
    if set(pin["files"]) != FILES:
        raise ValueError("Unexpected embedding file list")
    output.mkdir(parents=True, exist_ok=True)
    for name, expected in pin["files"].items():
        path = output / name
        incoming = path.with_suffix(".download")
        hasher = sha256()
        try:
            # URL uses a fixed HTTPS origin, validated revision, and allowlisted file names.
            with (
                urlopen(f"{MODEL}/resolve/{revision}/{name}", timeout=60) as data,  # noqa: S310
                incoming.open("wb") as file,
            ):
                for chunk in iter(lambda: data.read(1024 * 1024), b""):
                    hasher.update(chunk)
                    file.write(chunk)
            if hasher.hexdigest() != expected:
                raise ValueError(f"Embedding checksum mismatch: {name}")
            incoming.replace(path)
        finally:
            incoming.unlink(missing_ok=True)


if __name__ == "__main__":
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
