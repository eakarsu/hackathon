"""Vector store management using ChromaDB with efficient batching"""

import gc
import logging
from typing import List

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions, batch_utils

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB vector store operations with efficient batching"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.collection = None
        self._setup_client()
    
    def _setup_client(self):
        """Initialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(
            path=self.config.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Use embedding model - try local cache first, then download if needed
        try:
            # First try the local model cache
            embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="./model_cache/all-MiniLM-L6-v2"
            )
            logger.info("Using cached embedding model")
        except Exception as e:
            logger.warning(f"Local model cache not found ({e}), downloading model...")
            # Fall back to downloading the model
            embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("Using downloaded embedding model")
        
        self.collection = self.client.get_or_create_collection(
            name="json_data_store",
            embedding_function=embed_fn
        )
    
    def get_collection(self):
        """Get the ChromaDB collection"""
        return self.collection
    
    def index_documents(self, documents: List[str]):
        """Index documents in efficient batches"""
        logger.info(f"Indexing {len(documents)} documents in batches...")
        
        # Generate unique IDs
        ids = [f"doc_{i}" for i in range(len(documents))]
        
        # Use ChromaDB's built-in batching utility
        try:
            batches = batch_utils.create_batches(
                api=self.client,
                ids=ids,
                documents=documents
            )
            
            batch_count = 0
            for batch in batches:
                batch_ids, batch_embeddings, batch_metadatas, batch_documents = batch
                
                self.collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas
                )
                
                batch_count += 1
                logger.info(f"✅ Indexed batch {batch_count} ({len(batch_ids)} documents)")
                gc.collect()
            
            logger.info(f"🎉 Successfully indexed {len(documents)} documents in {batch_count} batches")
            
        except Exception as e:
            logger.error(f"Batch indexing failed: {e}")
            # Fallback to your existing method
            self._index_documents_individually(documents)
    
    def _index_documents_individually(self, documents: List[str]):
        """Fallback: Index documents one by one (your current method)"""
        logger.warning("Using fallback individual indexing...")
        
        for i, doc in enumerate(documents):
            try:
                self.collection.add(
                    documents=[doc],
                    ids=[f"doc_{i}"]
                )
                gc.collect()
            except Exception as e:
                logger.error(f"Failed to index document {i}: {e}")
    
    def query(self, question: str, n_results: int = 3) -> List[str]:
        """Query the vector store for relevant documents"""
        logger.info(f"Querying vector store: {question}")
        
        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=n_results
            )
            
            return results['documents'][0] if results['documents'] else []
        
        except Exception as e:
            logger.error(f"Vector store query failed: {e}")
            return []