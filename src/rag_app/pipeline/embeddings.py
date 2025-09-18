"""
Professional Embeddings Manager for RAG System
Handles embedding generation and management
"""

import logging
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Union
from sentence_transformers import SentenceTransformer
from django.db import transaction
from ..models import DocumentChunk, Document

logger = logging.getLogger(__name__)


class EmbeddingsError(Exception):
    """Custom exception for embeddings operations"""
    pass


class EmbeddingsManager:
    """
    Professional embeddings manager for RAG system
    
    Features:
    - Multiple embedding model support
    - Batch processing for efficiency
    - Database integration
    - Model caching and management
    - Performance monitoring
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embeddings manager
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            raise EmbeddingsError(f"Cannot load embedding model: {e}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            NumPy array of embeddings
        """
        try:
            if not self.model:
                raise EmbeddingsError("Model not loaded")
            
            if not text or not text.strip():
                raise EmbeddingsError("Empty text provided")
            
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise EmbeddingsError(f"Failed to generate embedding: {e}")
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of NumPy arrays
        """
        try:
            if not self.model:
                raise EmbeddingsError("Model not loaded")
            
            if not texts:
                return []
            
            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                raise EmbeddingsError("No valid texts provided")
            
            # Generate embeddings in batches
            embeddings = []
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]
                batch_embeddings = self.model.encode(batch, convert_to_tensor=False)
                embeddings.extend([emb.astype(np.float32) for emb in batch_embeddings])
            
            logger.info(f"Generated {len(embeddings)} embeddings in batches")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise EmbeddingsError(f"Failed to generate batch embeddings: {e}")
    
    def update_chunk_embeddings(self, 
                               chunk_ids: Optional[List[str]] = None,
                               document_id: Optional[str] = None,
                               subject_id: Optional[int] = None,
                               batch_size: int = 32) -> Dict[str, Any]:
        """
        Update embeddings for chunks
        
        Args:
            chunk_ids: Specific chunk IDs to update
            document_id: Update all chunks for a document
            subject_id: Update all chunks for a subject
            batch_size: Batch size for processing
            
        Returns:
            Dict with update statistics
        """
        try:
            start_time = logger.info("Starting chunk embedding update")
            
            # Build query for chunks to update
            if chunk_ids:
                chunks = DocumentChunk.objects.filter(id__in=chunk_ids)
            elif document_id:
                chunks = DocumentChunk.objects.filter(document_id=document_id)
            elif subject_id:
                chunks = DocumentChunk.objects.filter(document__subject_id=subject_id)
            else:
                # Update all chunks without embeddings
                chunks = DocumentChunk.objects.filter(embedding_vector__isnull=True)
            
            chunks = chunks.select_related('document')
            total_chunks = chunks.count()
            
            if total_chunks == 0:
                return {
                    'success': True,
                    'updated_count': 0,
                    'total_count': 0,
                    'message': 'No chunks found to update'
                }
            
            logger.info(f"Updating embeddings for {total_chunks} chunks")
            
            # Process in batches
            updated_count = 0
            error_count = 0
            
            for i in range(0, total_chunks, batch_size):
                batch_chunks = list(chunks[i:i + batch_size])
                
                try:
                    # Extract texts
                    texts = [chunk.content for chunk in batch_chunks]
                    
                    # Generate embeddings
                    embeddings = self.generate_embeddings_batch(texts, batch_size)
                    
                    # Update database
                    with transaction.atomic():
                        for chunk, embedding in zip(batch_chunks, embeddings):
                            try:
                                chunk.embedding_vector = pickle.dumps(embedding)
                                chunk.save(update_fields=['embedding_vector'])
                                updated_count += 1
                            except Exception as e:
                                logger.error(f"Error saving embedding for chunk {chunk.id}: {e}")
                                error_count += 1
                    
                    logger.info(f"Processed batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}")
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    error_count += len(batch_chunks)
                    continue
            
            result = {
                'success': True,
                'updated_count': updated_count,
                'error_count': error_count,
                'total_count': total_chunks,
                'model_used': self.model_name
            }
            
            logger.info(f"Embedding update completed: {updated_count} updated, {error_count} errors")
            return result
            
        except Exception as e:
            logger.error(f"Error updating chunk embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'total_count': 0
            }
    
    def regenerate_all_embeddings(self, batch_size: int = 32) -> Dict[str, Any]:
        """
        Regenerate all embeddings in the system
        
        Args:
            batch_size: Batch size for processing
            
        Returns:
            Dict with regeneration statistics
        """
        try:
            logger.info("Starting full embedding regeneration")
            
            # Clear existing embeddings
            with transaction.atomic():
                DocumentChunk.objects.update(embedding_vector=None)
            
            # Regenerate all embeddings
            result = self.update_chunk_embeddings(batch_size=batch_size)
            result['operation'] = 'full_regeneration'
            
            return result
            
        except Exception as e:
            logger.error(f"Error regenerating all embeddings: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': 'full_regeneration'
            }
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding statistics"""
        try:
            stats = {
                'model_name': self.model_name,
                'model_loaded': self.model is not None,
                'total_chunks': DocumentChunk.objects.count(),
                'chunks_with_embeddings': DocumentChunk.objects.filter(
                    embedding_vector__isnull=False
                ).count(),
                'chunks_without_embeddings': DocumentChunk.objects.filter(
                    embedding_vector__isnull=True
                ).count()
            }
            
            if self.model:
                # Get model dimensions if possible
                try:
                    sample_embedding = self.model.encode("test")
                    stats['embedding_dimension'] = len(sample_embedding)
                except:
                    stats['embedding_dimension'] = 'unknown'
            
            # Stats by document type
            from django.db.models import Count
            stats['embeddings_by_document_type'] = list(
                DocumentChunk.objects.filter(
                    embedding_vector__isnull=False
                ).values('document__document_type').annotate(
                    count=Count('id')
                )
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            return {'error': str(e)}
    
    def compare_embeddings(self, text1: str, text2: str) -> float:
        """
        Compare similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            emb1 = self.generate_embedding(text1)
            emb2 = self.generate_embedding(text2)
            
            # Calculate cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error comparing embeddings: {e}")
            return 0.0
    
    def find_similar_chunks(self, 
                           reference_text: str, 
                           subject_id: Optional[int] = None,
                           top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find chunks similar to reference text using embeddings
        
        Args:
            reference_text: Text to find similar chunks for
            subject_id: Optional subject ID to filter
            top_k: Number of similar chunks to return
            
        Returns:
            List of similar chunks with similarity scores
        """
        try:
            # Generate embedding for reference text
            ref_embedding = self.generate_embedding(reference_text)
            
            # Get chunks to compare against
            chunks_query = DocumentChunk.objects.filter(
                embedding_vector__isnull=False
            ).select_related('document')
            
            if subject_id:
                chunks_query = chunks_query.filter(document__subject_id=subject_id)
            
            chunks = chunks_query[:1000]  # Limit for performance
            
            similarities = []
            for chunk in chunks:
                try:
                    chunk_embedding = pickle.loads(chunk.embedding_vector)
                    
                    # Calculate cosine similarity
                    dot_product = np.dot(ref_embedding, chunk_embedding)
                    norm1 = np.linalg.norm(ref_embedding)
                    norm2 = np.linalg.norm(chunk_embedding)
                    
                    similarity = float(dot_product / (norm1 * norm2))
                    
                    similarities.append({
                        'chunk_id': str(chunk.id),
                        'similarity': similarity,
                        'content': chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                        'document_title': chunk.document.title,
                        'chunk_index': chunk.chunk_index
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing chunk {chunk.id}: {e}")
                    continue
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar chunks: {e}")
            return []
    
    def validate_embeddings(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        Validate stored embeddings
        
        Args:
            sample_size: Number of chunks to validate
            
        Returns:
            Validation results
        """
        try:
            chunks = DocumentChunk.objects.filter(
                embedding_vector__isnull=False
            ).order_by('?')[:sample_size]
            
            valid_count = 0
            invalid_count = 0
            dimension_counts = {}
            
            for chunk in chunks:
                try:
                    embedding = pickle.loads(chunk.embedding_vector)
                    
                    if isinstance(embedding, np.ndarray) and embedding.size > 0:
                        valid_count += 1
                        dim = embedding.shape[0] if embedding.ndim == 1 else embedding.size
                        dimension_counts[dim] = dimension_counts.get(dim, 0) + 1
                    else:
                        invalid_count += 1
                        
                except Exception:
                    invalid_count += 1
            
            return {
                'sample_size': len(chunks),
                'valid_embeddings': valid_count,
                'invalid_embeddings': invalid_count,
                'dimension_distribution': dimension_counts,
                'validation_passed': invalid_count == 0
            }
            
        except Exception as e:
            logger.error(f"Error validating embeddings: {e}")
            return {'error': str(e)}


# Global embeddings manager instance
_embeddings_manager = None

def get_embeddings_manager(model_name: str = 'all-MiniLM-L6-v2') -> EmbeddingsManager:
    """Get or create global embeddings manager instance"""
    global _embeddings_manager
    if _embeddings_manager is None or _embeddings_manager.model_name != model_name:
        _embeddings_manager = EmbeddingsManager(model_name)
    return _embeddings_manager
