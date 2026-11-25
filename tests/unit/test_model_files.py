from hashlib import sha256

import pytest

from backend.retrieval.model_files import verify_embedding_files


def test_embedding_files_fail_closed_after_one_byte_changes(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    fixture = b"CANARY-T36-1cbe"
    weights = model / "model.safetensors"
    weights.write_bytes(fixture)
    manifest = tmp_path / "models.lock"
    manifest.write_text(
        f'[embedding.files]\n"model.safetensors" = "{sha256(fixture).hexdigest()}"\n',
        encoding="utf-8",
    )

    assert verify_embedding_files(model, manifest) == model
    weights.write_bytes(fixture[:-1] + b"f")
    with pytest.raises(ValueError, match="Embedding checksum mismatch"):
        verify_embedding_files(model, manifest)
