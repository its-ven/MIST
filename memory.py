import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from chromadb.types import Where, WhereDocument
from typing import Literal
from utils import log, LogType, get_dir, get_caller_path, _boot_padding
from huggingface_hub import snapshot_download
from tqdm.auto import tqdm
import logging

logging.getLogger("chromadb").setLevel(logging.CRITICAL)

active_embeddings = {}

class Device:
    cpu = "cpu"
    cuda = "cuda"
    auto = None

class Embedding:
    fast = "all-MiniLM-L6-v2"
    balanced = "all-distilroberta-v1"
    precise = "all-mpnet-base-v2"

def _get_embedding(embedding: Embedding, device: Device):
    global active_embeddings
    if not get_dir(f"embeddings/{embedding}"):
        log(LogType.download, f"[Memory] Downloading embedding: {embedding}...", with_prefix=False)
        snapshot_download(f"sentence-transformers/{embedding}", local_dir=f"./embeddings/{embedding}", tqdm_class=tqdm)
    if embedding not in active_embeddings:
        embedding_instance = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=f"./embeddings/{embedding}", device=device)
        active_embeddings[embedding] = embedding_instance
    return active_embeddings[embedding]

class ExternalMemory:
    def __init__(self, persona_name: str, embedding: Embedding = Embedding.balanced, device = Device.auto):
        log(LogType.boot_sequence, _boot_padding(f"[Memory] Loading external memory..."))
        _embedding = _get_embedding(embedding, device)
        self.client = chromadb.PersistentClient(f"./personas/{persona_name}/memories/external", settings=ChromaSettings(anonymized_telemetry=False))
        self.index = self.client.get_or_create_collection("index", embedding_function=_embedding, metadata={"hnsw:space": "cosine"})

    def delete(self, where: Where = None, where_document: WhereDocument = None):
        self.index.delete(where=where, where_document=where_document)

    def add(self, content: str):
        _id = str(self.index.count() + 1)
        self.index.add(ids=[_id], documents=[content])
    
    def query(self, queries: list):
        min_score = 0.5
        max_per_query = 5
        get_score = lambda x: round(1 - (x / 2), 3)
        seen_ids = set()
        memories = []
        for query in queries:
            query_results = self.index.query(query_texts=[query], n_results=max_per_query)
            for i in range(len(query_results["ids"][0])):
                _id = int(query_results["ids"][0][i])
                if _id not in seen_ids:
                    seen_ids.add(_id)
                    score = get_score(query_results["distances"][0][i])
                    if score >= min_score:
                        memories.append(query_results["documents"][0][i])
        if memories:
            return memories
        else:
            return "No relevant external memories found!"

class InternalMemory:
    def __init__(self, persona_name: str, embedding: Embedding = Embedding.balanced, device: Device = Device.auto):
        log(LogType.boot_sequence, _boot_padding(f"[Memory] Loading internal memory..."))
        _embedding = _get_embedding(embedding, device)
        self.client = chromadb.PersistentClient(f"./personas/{persona_name}/memories/internal", settings=ChromaSettings(anonymized_telemetry=False))
        self.index = self.client.get_or_create_collection("index", embedding_function=_embedding, metadata={"hnsw:space": "cosine"})

    def add(self, content: list, source: str):
        for entry in content:
            self.index.add(ids=[str(self.index.count()+1)], documents=[entry], metadatas=[{"source": source}])
    
    def query(self, queries: list, source: str):
        min_score = 0.5
        max_per_query = 5
        get_score = lambda x: round(1 - (x / 2), 3)
        seen_ids = set()
        memories = []
        for query in queries:
            query_results = self.index.query(query_texts=[query], n_results=max_per_query, where={"source": {"$eq": source}})
            for i in range(len(query_results["ids"][0])):
                _id = int(query_results["ids"][0][i])
                if _id not in seen_ids:
                    seen_ids.add(_id)
                    score = get_score(query_results["distances"][0][i])
                    if score >= min_score:
                        memories.append(query_results["documents"][0][i])
        if memories:
            return "\n".join([f"- {memory}" for memory in memories])
        else:
            return "No relevant memories found!"
