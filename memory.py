import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from chromadb.types import Where, WhereDocument
from typing import Literal
from utils import log, LogType, get_dir, get_caller_path
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

class FunctionMemory:
    """
        ChromaDB wrapper for simple function-specific memory.
    """
    def __init__(self, function_name: str, embedding: Embedding = Embedding.balanced, device = Device.auto):
        module_path = get_caller_path()
        log(LogType.system, f"[Memory] Loading embeddings for {function_name}...")
        _embedding = _get_embedding(embedding, device)
        self.client = chromadb.PersistentClient(f"{module_path}/{function_name}", settings=ChromaSettings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(function_name, embedding_function=_embedding, metadata={"hnsw:space": "cosine"})

    def delete(self, where: Where = None, where_document: WhereDocument = None):
        self.collection.delete(where=where, where_document=where_document)

    def add(self, content: dict):
        _id = str(self.collection.count() + 1)
        self.collection.add(ids=[_id], documents=[str(content)])
    
    def query(self, query: str, n_results: int = 5, min_score: int = 0.4, where: Where = None, where_document: WhereDocument = None) -> list[dict] | None:
        get_score = lambda x: round(1 - (x / 2), 3)
        query_results = self.collection.query(query_texts=[query], n_results=n_results, where=where, where_document=where_document)
        min_found = get_score(min(query_results["distances"][0]))
        results = []
        for i in range(n_results):
            try:
                distance = query_results["distances"][0][i]
                score = get_score(distance)
                if score >= min_score:
                    document = query_results["documents"][0][i]
                    metadata = query_results["metadatas"][0][i]
                    _id = int(query_results["ids"][0][i])
                    results.append({"id": _id, "content": document, "metadata": metadata, "score": score})
            except:
                pass
        if results:
            return results
        else:
            log(LogType.warning, f"[Memory] No memories found in {self.collection.name} with minimum score {min_score}! (Min: {min_found})")

class PersonaMemory:
    def __init__(self, persona_name: str, embedding: Embedding = Embedding.balanced, device: Device = Device.auto):
        log(LogType.system, f"[Memory] Loading persona memory...")
        _embedding = _get_embedding(embedding, device)
        self.client = chromadb.PersistentClient(f"./personas/{persona_name}/memories", settings=ChromaSettings(anonymized_telemetry=False))
        self.index = self.client.get_or_create_collection("index", embedding_function=_embedding, metadata={"hnsw:space": "cosine"})

    def append_session_events(self, session_id: int, content: list):
        for entry in content:
            self.index.add(ids=[str(self.index.count()+1)], documents=[entry], metadatas=[{"session_id": session_id}])
    
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
            return "\n".join([f"- {memory}" for memory in memories])
        else:
            return "No memories found!"
