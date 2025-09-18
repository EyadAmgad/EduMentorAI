"""
Professional Vector Store for RAG System
Handles vector similarity search and retrieval using FAISS and embeddings
"""

import logging
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import faiss
from sentence_transformers import SentenceTransformer
from django.db.models import Q
from ..models import DocumentChunk, Document, Subject

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Custom exception for vector store operations"""
    pass


class VectorStore:
    """
    Professional vector store for RAG document retrieval
    
    Features:
    - FAISS-based similarity search
    - Subject-specific document filtering
    - Hybrid search (semantic + keyword)
    - Caching for performance
    - Comprehensive logging
    """
    
    def __init__(self, embedding_model: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the vector store
        
        Args:
            embedding_model: Name of the sentence transformer model
        """
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.index = None
        self.chunk_ids = []  # Maps FAISS index positions to chunk IDs
        self.last_build_time = None
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise VectorStoreError(f"Cannot initialize embedding model: {e}")
    
    def build_index(self, subject_id: Optional[int] = None, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build or rebuild the FAISS index
        
        Args:
            subject_id: Optional subject ID to filter documents
            force_rebuild: Force rebuilding even if index exists
            
        Returns:
            Dict with build statistics
        """
        try:
            logger.info(f"Building vector index for subject {subject_id}")
            
            # Get chunks to index
            if subject_id:
                chunks = DocumentChunk.objects.filter(
                    document__subject_id=subject_id,
                    document__processed=True,
                    embedding_vector__isnull=False
                ).select_related('document').order_by('document__title', 'chunk_index')
            else:
                chunks = DocumentChunk.objects.filter(
                    document__processed=True,
                    embedding_vector__isnull=False
                ).select_related('document').order_by('document__title', 'chunk_index')
            
            if not chunks.exists():
                logger.warning("No chunks with embeddings found")
                return {
                    'success': False,
                    'error': 'No processed documents with embeddings found',
                    'chunks_count': 0
                }
            
            # Extract embeddings and chunk IDs
            embeddings = []
            chunk_ids = []
            
            for chunk in chunks:
                try:
                    embedding = pickle.loads(chunk.embedding_vector)
                    embeddings.append(embedding)
                    chunk_ids.append(chunk.id)
                except Exception as e:
                    logger.warning(f"Failed to load embedding for chunk {chunk.id}: {e}")
                    continue
            
            if not embeddings:
                return {
                    'success': False,
                    'error': 'No valid embeddings found',
                    'chunks_count': 0
                }
            
            # Create FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            dimension = embeddings_array.shape[1]
            
            # Use IndexFlatIP for cosine similarity (after normalization)
            self.index = faiss.IndexFlatIP(dimension)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_array)
            
            # Add to index
            self.index.add(embeddings_array)
            self.chunk_ids = chunk_ids
            
            result = {
                'success': True,
                'chunks_count': len(embeddings),
                'index_dimension': dimension,
                'subject_id': subject_id
            }
            
            logger.info(f"Built vector index with {len(embeddings)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Error building vector index: {e}")
            return {
                'success': False,
                'error': str(e),
                'chunks_count': 0
            }
    
    def search(self, 
               query: str, 
               subject_id: Optional[int] = None,
               k: int = 5,
               score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            subject_id: Optional subject ID to filter results
            k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with metadata
        """
        try:
            # Build index if not exists or if subject filtering changed
            if self.index is None or (subject_id and not self._is_index_for_subject(subject_id)):
                build_result = self.build_index(subject_id)
                if not build_result['success']:
                    return []
            
            # Encode query
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding, min(k, len(self.chunk_ids)))
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    continue
                    
                if score < score_threshold:
                    continue
                
                try:
                    chunk_id = self.chunk_ids[idx]
                    chunk = DocumentChunk.objects.select_related('document', 'document__subject').get(id=chunk_id)
                    
                    result = {
                        'chunk_id': str(chunk.id),
                        'content': chunk.content,
                        'score': float(score),
                        'document_id': str(chunk.document.id),
                        'document_title': chunk.document.title,
                        'document_type': chunk.document.document_type,
                        'subject_id': str(chunk.document.subject.id) if chunk.document.subject else None,
                        'subject_name': chunk.document.subject.name if chunk.document.subject else None,
                        'page_number': chunk.page_number,
                        'chunk_index': chunk.chunk_index
                    }
                    
                    results.append(result)
                    
                except DocumentChunk.DoesNotExist:
                    logger.warning(f"Chunk {chunk_id} not found in database")
                    continue
                except Exception as e:
                    logger.error(f"Error processing search result {idx}: {e}")
                    continue
            
            logger.info(f"Found {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def hybrid_search(self,
                      query: str,
                      subject_id: Optional[int] = None,
                      k: int = 5,
                      semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword matching
        
        Args:
            query: Search query
            subject_id: Optional subject ID to filter results
            k: Number of results to return
            semantic_weight: Weight for semantic search (1 - semantic_weight for keyword)
            
        Returns:
            List of hybrid search results
        """
        try:
            # Get semantic search results
            semantic_results = self.search(query, subject_id, k * 2)  # Get more for reranking
            
            # Get keyword search results
            keyword_results = self._keyword_search(query, subject_id, k * 2)
            
            # Combine and rerank results
            combined_results = self._combine_search_results(
                semantic_results, keyword_results, semantic_weight
            )
            
            return combined_results[:k]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return self.search(query, subject_id, k)  # Fallback to semantic search
    
    def _keyword_search(self, query: str, subject_id: Optional[int] = None, k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search on document chunks
        """
        try:
            # Build query filter
            chunks_query = Q(content__icontains=query)
            
            if subject_id:
                chunks_query &= Q(document__subject_id=subject_id)
            
            chunks_query &= Q(document__processed=True)
            
            # Search chunks
            chunks = DocumentChunk.objects.filter(chunks_query).select_related(
                'document', 'document__subject'
            ).order_by('-document__uploaded_at')[:k]
            
            results = []
            for chunk in chunks:
                # Simple keyword scoring (count of query words in content)
                query_words = query.lower().split()
                content_lower = chunk.content.lower()
                keyword_score = sum(content_lower.count(word) for word in query_words) / len(query_words)
                
                result = {
                    'chunk_id': str(chunk.id),
                    'content': chunk.content,
                    'score': keyword_score,
                    'document_id': str(chunk.document.id),
                    'document_title': chunk.document.title,
                    'document_type': chunk.document.document_type,
                    'subject_id': str(chunk.document.subject.id) if chunk.document.subject else None,
                    'subject_name': chunk.document.subject.name if chunk.document.subject else None,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index
                }
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def _combine_search_results(self,
                                semantic_results: List[Dict[str, Any]],
                                keyword_results: List[Dict[str, Any]],
                                semantic_weight: float) -> List[Dict[str, Any]]:
        """
        Combine and rerank semantic and keyword search results
        """
        # Create a map of chunk_id to results
        combined = {}
        
        # Add semantic results
        for result in semantic_results:
            chunk_id = result['chunk_id']
            combined[chunk_id] = result.copy()
            combined[chunk_id]['semantic_score'] = result['score']
            combined[chunk_id]['keyword_score'] = 0.0
        
        # Add keyword results
        for result in keyword_results:
            chunk_id = result['chunk_id']
            if chunk_id in combined:
                combined[chunk_id]['keyword_score'] = result['score']
            else:
                combined[chunk_id] = result.copy()
                combined[chunk_id]['semantic_score'] = 0.0
                combined[chunk_id]['keyword_score'] = result['score']
        
        # Calculate combined scores
        for chunk_id, result in combined.items():
            semantic_score = result.get('semantic_score', 0.0)
            keyword_score = result.get('keyword_score', 0.0)
            
            # Normalize scores (simple min-max normalization)
            combined_score = (semantic_weight * semantic_score + 
                             (1 - semantic_weight) * keyword_score)
            
            result['score'] = combined_score
            result['search_type'] = 'hybrid'
        
        # Sort by combined score
        results = list(combined.values())
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _is_index_for_subject(self, subject_id: int) -> bool:
        """
        Check if current index is built for the specified subject
        Simple implementation - in production, you might want more sophisticated caching
        """
        # For now, we'll rebuild the index each time for subject-specific searches
        return False
    
    def get_similar_chunks(self, chunk_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find chunks similar to a given chunk
        
        Args:
            chunk_id: ID of the source chunk
            k: Number of similar chunks to return
            
        Returns:
            List of similar chunks
        """
        try:
            # Get the source chunk
            source_chunk = DocumentChunk.objects.select_related('document').get(id=chunk_id)
            
            if not source_chunk.embedding_vector:
                logger.warning(f"Chunk {chunk_id} has no embedding")
                return []
            
            # Use the chunk's content as query
            return self.search(
                query=source_chunk.content[:200],  # Use first 200 chars as query
                subject_id=source_chunk.document.subject.id if source_chunk.document.subject else None,
                k=k + 1  # +1 because the source chunk will be in results
            )[1:]  # Remove the first result (the source chunk itself)
            
        except DocumentChunk.DoesNotExist:
            logger.error(f"Chunk {chunk_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error finding similar chunks: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            stats = {
                'index_built': self.index is not None,
                'chunks_in_index': len(self.chunk_ids) if self.chunk_ids else 0,
                'total_chunks_with_embeddings': DocumentChunk.objects.filter(
                    embedding_vector__isnull=False
                ).count(),
                'total_processed_documents': Document.objects.filter(processed=True).count(),
                'embedding_model': self.embedding_model_name
            }
            
            if self.index:
                stats['index_dimension'] = self.index.d
                stats['index_type'] = type(self.index).__name__
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting vector store stats: {e}")
            return {'error': str(e)}
    
    def clear_index(self):
        """Clear the current index"""
        self.index = None
        self.chunk_ids = []
        logger.info("Vector index cleared")
    
    def update_chunk_embedding(self, chunk_id: str):
        """
        Update embedding for a specific chunk
        Note: This requires rebuilding the index in this simple implementation
        """
        try:
            chunk = DocumentChunk.objects.get(id=chunk_id)
            
            if not chunk.content:
                logger.warning(f"Chunk {chunk_id} has no content")
                return False
            
            # Generate new embedding
            embedding = self.embedding_model.encode(chunk.content)
            chunk.embedding_vector = pickle.dumps(embedding.astype(np.float32))
            chunk.save()
            
            logger.info(f"Updated embedding for chunk {chunk_id}")
            
            # Clear index to force rebuild
            self.clear_index()
            
            return True
            
        except DocumentChunk.DoesNotExist:
            logger.error(f"Chunk {chunk_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating chunk embedding: {e}")
            return False
