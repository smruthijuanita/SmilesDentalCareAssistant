import faiss
import numpy as np
import os
import json
from typing import List

# Prefer sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

VECTOR_DIR = "vector_store"
os.makedirs(VECTOR_DIR, exist_ok=True)

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class RAGPipeline:
    """RAG pipeline using Dense Vectorization (SBERT) and MMR Retrieval."""

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.index = None
        self.text_chunks = []
        self.index_path = f"{VECTOR_DIR}/user_{user_id}.faiss"
        self.meta_path = f"{VECTOR_DIR}/user_{user_id}_meta.json"
        self.sbert = None

        if SentenceTransformer is not None:
            try:
                self.sbert = SentenceTransformer(EMBED_MODEL_NAME)
            except Exception:
                self.sbert = None
        
        if os.path.exists(self.index_path):
            self.load_index()

    def chunk_text(self, text, chunk_size=600, overlap=150):
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = max(end - overlap, start + 1)
        return chunks

    def embed(self, texts):
        if self.sbert is not None:
            try:
                embs = self.sbert.encode(texts, convert_to_numpy=True)
                return embs.astype("float32")
            except Exception:
                pass
        
        # Fallback or error if no model
        return None

    def build_index(self, pdf_text):
        if not self.sbert:
            return

        self.text_chunks = self.chunk_text(pdf_text)
        embeddings = self.embed(self.text_chunks)
        
        if embeddings is None or len(embeddings) == 0:
            self.index = None
            return

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

        # save FAISS index
        try:
            faiss.write_index(self.index, self.index_path)
        except Exception:
            pass

        # save metadata
        try:
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self.text_chunks, f)
        except Exception:
            pass

    def load_index(self):
        try:
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.text_chunks = json.load(f)
        except Exception:
            self.index = None
            self.text_chunks = []

    def maximal_marginal_relevance(self, query_embedding, chunk_embeddings, top_k=4, lambda_mult=0.5):
        """
        MMR algorithm to select top_k diverse chunks.
        """
        if chunk_embeddings is None or len(chunk_embeddings) == 0:
            return []

        # Calculate cosine similarity between query and all chunks
        # Note: FAISS IndexFlatL2 uses Euclidean distance, but for MMR we usually want cosine similarity.
        # We can compute dot product if vectors are normalized.
        # For simplicity with numpy:
        
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Ensure 2D arrays
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        sims_to_query = cosine_similarity(query_embedding, chunk_embeddings)[0]
        
        selected_indices = []
        candidate_indices = list(range(len(chunk_embeddings)))

        for _ in range(top_k):
            best_score = -float('inf')
            best_idx = -1

            for idx in candidate_indices:
                # Relevance part
                relevance = sims_to_query[idx]
                
                # Diversity part
                if not selected_indices:
                    diversity = 0
                else:
                    # Max sim to already selected
                    selected_embs = chunk_embeddings[selected_indices]
                    candidate_emb = chunk_embeddings[idx].reshape(1, -1)
                    diversity = np.max(cosine_similarity(candidate_emb, selected_embs))
                
                mmr_score = (lambda_mult * relevance) - ((1 - lambda_mult) * diversity)
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx != -1:
                selected_indices.append(best_idx)
                candidate_indices.remove(best_idx)
            else:
                break
                
        return selected_indices

    def retrieve(self, query, top_k=4):
        if not self.index or len(self.text_chunks) == 0 or not self.sbert:
            return []

        q_emb = self.embed([query])
        if q_emb is None:
            return []

        # For MMR, we need to fetch more candidates first, then rerank.
        # Fetch 4x top_k candidates
        fetch_k = min(len(self.text_chunks), top_k * 4)
        D, I = self.index.search(q_emb, fetch_k)
        
        candidate_indices = I[0]
        candidate_chunks = [self.text_chunks[i] for i in candidate_indices if i != -1]
        
        # We need embeddings of candidates for MMR. 
        # Ideally we should store them or re-compute. Re-computing is safer if we didn't store them.
        # Since we use SBERT, re-computing for small number of candidates is fast.
        candidate_embeddings = self.embed(candidate_chunks)
        
        if candidate_embeddings is None:
            return candidate_chunks[:top_k]

        # Apply MMR
        selected_relative_indices = self.maximal_marginal_relevance(q_emb, candidate_embeddings, top_k=top_k)
        
        final_chunks = [candidate_chunks[i] for i in selected_relative_indices]
        return final_chunks
