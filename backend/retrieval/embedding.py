"""CPU embeddings from verified, local BGE assets."""

from collections.abc import Callable
from pathlib import Path

from backend.retrieval.model_files import verify_embedding_files


def load_embedding(
    model_dir: Path = Path("/opt/models/bge-small-en-v1.5"),
    manifest: Path = Path("/opt/models/models.lock"),
) -> Callable[[str], list[float]]:
    """Load local safetensors and return a normalized, 384-dimensional encoder."""
    path = verify_embedding_files(model_dir, manifest)

    import torch
    from transformers import BertModel, BertTokenizerFast

    tokenizer = BertTokenizerFast.from_pretrained(path, local_files_only=True)
    model = BertModel.from_pretrained(path, local_files_only=True, use_safetensors=True)
    model.eval()

    def embed(text: str) -> list[float]:
        inputs = tokenizer(text, truncation=True, max_length=512, return_tensors="pt")
        with torch.inference_mode():
            pooled = model(**inputs).last_hidden_state[:, 0]
            return torch.nn.functional.normalize(pooled, p=2, dim=1)[0].tolist()

    return embed
