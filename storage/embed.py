import numpy as np
from langchain_voyageai import VoyageAIEmbeddings

MODEL = "voyage-3.5-lite"
BATCH_SIZE = 128


def embed_texts(texts: list[str], api_key: str) -> list[bytes]:
    embedder = VoyageAIEmbeddings(model=MODEL, api_key=api_key, batch_size=BATCH_SIZE)
    vectors = embedder.embed_documents(texts)
    return [np.array(vec, dtype=np.float32).tobytes() for vec in vectors]
