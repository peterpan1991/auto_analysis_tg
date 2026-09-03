from typing import List, Dict, Optional
import chromadb

from core.constants import RAG_CANDIDATE_TOP_K, VECTOR_DB_PATH

class ChromaDBClient:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        return cls._instance

    def get_collection(self, task_id: int):
        return self._client.get_or_create_collection(name=f"task_{task_id}")

    def upsert_embeddings(
        self,
        task_id: int,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        documents: List[str]
    ):
        collection = self.get_collection(task_id)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

    def query(
        self,
        task_id: int,
        query_embedding: List[float],
        n_results: int = RAG_CANDIDATE_TOP_K,
        contact_id: int = None,
        document_contains_any: Optional[List[str]] = None,
    ) -> Dict:
        collection = self.get_collection(task_id)

        where_filter = None

        if contact_id is not None:
            where_filter = {"contact_id": contact_id}

        where_document_filter = None

        if document_contains_any:
            contains_filters = [
                {"$contains": value}
                for value in document_contains_any
            ]

            if len(contains_filters) == 1:
                where_document_filter = contains_filters[0]
            else:
                where_document_filter = {"$or": contains_filters}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            where_document=where_document_filter
        )
        return results

    def count(self, task_id: int) -> int:
        collection = self.get_collection(task_id)
        return collection.count()

    def delete_collection(self, task_id: int):
        try:
            self._client.delete_collection(name=f"task_{task_id}")
        except:
            pass

chroma_client = ChromaDBClient()

def get_chroma_collection(task_id: int):
    return chroma_client.get_collection(task_id)

def format_query_results(results: Dict) -> List[Dict]:
    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    formatted_results = []
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    for i in range(len(results["ids"][0])):
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        formatted_results.append({
            "chunk_id": results["ids"][0][i],
            "contact_id": metadata.get("contact_id", 0),
            "start_message_id": metadata.get("start_message_id", 0),
            "end_message_id": metadata.get("end_message_id", 0),
            "message_count": metadata.get("message_count", 0),
            "content": documents[i] if i < len(documents) else metadata.get("content", ""),
            "sender": metadata.get("sender", "Unknown"),
            "timestamp": metadata.get("timestamp", None),
            "similarity": round(1 / (1 + results["distances"][0][i]), 4) if results.get("distances") else 0
        })

    return formatted_results
