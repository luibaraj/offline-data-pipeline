import json
import time
import logging
import urllib.request
import urllib.error
import numpy as np

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
MODEL = "voyage-3.5-lite"
BATCH_SIZE = 128

logger = logging.getLogger(__name__)


def _call_voyage(texts: list[str], api_key: str) -> list[list[float]]:
    payload = json.dumps({"input": texts, "model": MODEL}).encode()
    for attempt in range(3):
        req = urllib.request.Request(
            VOYAGE_URL,
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = json.loads(resp.read())
                return [item["embedding"] for item in body["data"]]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 2 ** attempt
                logger.warning("Rate limited by Voyage AI, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Voyage AI rate limit exceeded after 3 attempts")


def embed_texts(texts: list[str], api_key: str) -> list[bytes]:
    """Embed texts in batches of 128; return float32 byte arrays."""
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vectors = _call_voyage(batch, api_key)
        for vec in vectors:
            results.append(np.array(vec, dtype=np.float32).tobytes())
    return results
