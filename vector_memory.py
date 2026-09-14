import hashlib
import math
import os 
import uuis
from datatime import datetime , timezone
from typing import List 

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

COLLECTION_NAME = "lession_failures"
EMBED_DIM = 128
PERMANENT_FIX_THRESHOLD =2
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "vector_store")

class VectorMemory:
    def __init__(self , path:str = DEFAULT_PATH):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME, embedding_function=HashingEmbedder()
        )

        #---------------------------------------------------------
        #writes
        #---------------------------------------------------------
        def record_attempt(self , topic:str , attempt_num:int , failures:list , passed:list):
            ts = datetime.now(timezone.utc).isoformat()
            for f in failures:
                self.collection.add(
                    ids=[str(uuid.uuid4())],
                    documents=[f"{f.name}: {f.reason}"],
                    metadatas=[{
                    "topic": topic,
                    "checkpoint": f.name,
                    "attempt": attempt_num,
                    "passed": passed,
                    "timestamp": ts,
                }],

                )
        
        #----------------------------------------------------------
        #reads
        #----------------------------------------------------------
        def retrieve_relevant_notes(self , topic: str , k:int = 3)->List[str]:
            if self.collection.count() == 0:
                return []
            k = min(k , self.collection.count())
            res = self.collection.query(query_texts=[topic], n_results=k)

            notes = []
            for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            if meta["topic"] == topic:
                notes.append(f"On a previous attempt at THIS topic, it failed: {doc}")
            else:
                notes.append(f"On the topic \"{meta['topic']}\", a similar lesson failed: {doc}")

            return notes
        

