"""
Professional Retriever for RAG System
Handles document retrieval and context preparation for LLM queries
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q
from .vectorstore import VectorStore
from ..models import DocumentChunk, Document, Subject

logger = logging.getLogger(__name__)


class RetrieverError(Exception):
    """Custom exception for retriever operations"""
    pass


class DocumentRetriever:
    """
    Professional document retriever for RAG system
    
    Features:
    - Vector-based similarity search
    - Subject-specific filtering
    - Context preparation and ranking
    - Multiple retrieval strategies
    - Comprehensive logging
    """
    
    def __init__(self, 
                 embedding_model: str = 'all-MiniLM-L6-v2',
                 max_context_length: int = 4000):
        """
        Initialize the document retriever
        
        Args:
            embedding_model: Name of the sentence transformer model
            max_context_length: Maximum length of combined context
        """
        self.vector_store = VectorStore(embedding_model)
        self.max_context_length = max_context_length
        
    def retrieve_for_query(self,
                          query: str,
                          subject_id: Optional[int] = None,
                          document_id: Optional[int] = None,
                          retrieval_strategy: str = 'hybrid',
                          max_chunks: int = 5,
                          score_threshold: float = 0.1) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User query
            subject_id: Optional subject ID to filter documents
            document_id: Optional document ID to filter to a specific document
            retrieval_strategy: 'semantic', 'keyword', or 'hybrid'
            max_chunks: Maximum number of chunks to retrieve
            score_threshold: Minimum relevance score
            
        Returns:
            Dict with retrieved chunks and metadata
        """
        try:
            logger.info(f"Retrieving documents for query: {query[:50]}...")
            
            # Choose retrieval strategy
            if retrieval_strategy == 'semantic':
                chunks = self.vector_store.search(
                    query=query,
                    subject_id=subject_id,
                    document_id=document_id,
                    k=max_chunks,
                    score_threshold=score_threshold
                )
            elif retrieval_strategy == 'hybrid':
                chunks = self.vector_store.hybrid_search(
                    query=query,
                    subject_id=subject_id,
                    document_id=document_id,
                    k=max_chunks
                )
            elif retrieval_strategy == 'keyword':
                chunks = self._keyword_only_search(query, subject_id, document_id, max_chunks)
            else:
                raise RetrieverError(f"Unknown retrieval strategy: {retrieval_strategy}")
            
            if not chunks:
                logger.warning(f"No relevant documents found for query: {query[:50]}...")
                return {
                    'success': False,
                    'chunks': [],
                    'context': '',
                    'metadata': {
                        'query': query,
                        'strategy': retrieval_strategy,
                        'subject_id': subject_id,
                        'document_id': document_id,
                        'chunks_found': 0
                    }
                }
            
            # Prepare context
            context = self._prepare_context(chunks)
            
            # Add retrieval metadata
            metadata = {
                'query': query,
                'strategy': retrieval_strategy,
                'subject_id': subject_id,
                'document_id': document_id,
                'chunks_found': len(chunks),
                'context_length': len(context),
                'avg_score': sum(chunk['score'] for chunk in chunks) / len(chunks),
                'documents_used': list(set(chunk['document_id'] for chunk in chunks))
            }
            
            result = {
                'success': True,
                'chunks': chunks,
                'context': context,
                'metadata': metadata
            }
            
            logger.info(f"Retrieved {len(chunks)} chunks for query")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return {
                'success': False,
                'chunks': [],
                'context': '',
                'metadata': {'error': str(e)}
            }
    
    def retrieve_for_subject(self,
                            subject_id: int,
                            query: Optional[str] = None,
                            max_chunks: int = 10) -> Dict[str, Any]:
        """
        Retrieve all relevant documents for a subject
        
        Args:
            subject_id: Subject ID
            query: Optional query to filter results
            max_chunks: Maximum number of chunks to return
            
        Returns:
            Dict with subject documents and metadata
        """
        try:
            logger.info(f"Retrieving documents for subject {subject_id}")
            
            if query:
                # Use query-based retrieval within subject
                return self.retrieve_for_query(
                    query=query,
                    subject_id=subject_id,
                    max_chunks=max_chunks
                )
            else:
                # Get all chunks for subject
                chunks = DocumentChunk.objects.filter(
                    document__subject_id=subject_id,
                    document__processed=True
                ).select_related('document', 'document__subject').order_by(
                    'document__title', 'chunk_index'
                )[:max_chunks]
                
                # Convert to consistent format
                formatted_chunks = []
                for chunk in chunks:
                    formatted_chunks.append({
                        'chunk_id': str(chunk.id),
                        'content': chunk.content,
                        'score': 1.0,  # No scoring for subject-wide retrieval
                        'document_id': str(chunk.document.id),
                        'document_title': chunk.document.title,
                        'document_type': chunk.document.document_type,
                        'subject_id': str(chunk.document.subject.id),
                        'subject_name': chunk.document.subject.name,
                        'page_number': chunk.page_number,
                        'chunk_index': chunk.chunk_index
                    })
                
                context = self._prepare_context(formatted_chunks)
                
                return {
                    'success': True,
                    'chunks': formatted_chunks,
                    'context': context,
                    'metadata': {
                        'subject_id': subject_id,
                        'chunks_found': len(formatted_chunks),
                        'context_length': len(context)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error retrieving subject documents: {e}")
            return {
                'success': False,
                'chunks': [],
                'context': '',
                'metadata': {'error': str(e)}
            }
    
    def retrieve_similar_to_chunk(self,
                                  chunk_id: str,
                                  max_chunks: int = 5) -> Dict[str, Any]:
        """
        Retrieve chunks similar to a given chunk
        
        Args:
            chunk_id: ID of the reference chunk
            max_chunks: Maximum number of similar chunks to return
            
        Returns:
            Dict with similar chunks and metadata
        """
        try:
            similar_chunks = self.vector_store.get_similar_chunks(chunk_id, max_chunks)
            context = self._prepare_context(similar_chunks)
            
            return {
                'success': True,
                'chunks': similar_chunks,
                'context': context,
                'metadata': {
                    'reference_chunk_id': chunk_id,
                    'chunks_found': len(similar_chunks),
                    'context_length': len(context)
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving similar chunks: {e}")
            return {
                'success': False,
                'chunks': [],
                'context': '',
                'metadata': {'error': str(e)}
            }
    
    def _keyword_only_search(self,
                            query: str,
                            subject_id: Optional[int] = None,
                            document_id: Optional[int] = None,
                            max_chunks: int = 5) -> List[Dict[str, Any]]:
        """
        Perform keyword-only search
        """
        try:
            # Build query filter
            chunks_query = Q()
            
            # Split query into words and search for each
            query_words = query.lower().split()
            for word in query_words:
                chunks_query |= Q(content__icontains=word)
            
            if document_id:
                # Filter by specific document (takes precedence over subject_id)
                chunks_query &= Q(document_id=document_id)
            elif subject_id:
                chunks_query &= Q(document__subject_id=subject_id)
            
            chunks_query &= Q(document__processed=True)
            
            # Search chunks
            chunks = DocumentChunk.objects.filter(chunks_query).select_related(
                'document', 'document__subject'
            ).order_by('-document__uploaded_at')[:max_chunks]
            
            results = []
            for chunk in chunks:
                # Calculate keyword relevance score
                content_lower = chunk.content.lower()
                score = sum(content_lower.count(word) for word in query_words) / len(query_words)
                
                results.append({
                    'chunk_id': str(chunk.id),
                    'content': chunk.content,
                    'score': score,
                    'document_id': str(chunk.document.id),
                    'document_title': chunk.document.title,
                    'document_type': chunk.document.document_type,
                    'subject_id': str(chunk.document.subject.id) if chunk.document.subject else None,
                    'subject_name': chunk.document.subject.name if chunk.document.subject else None,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index
                })
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def _prepare_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from retrieved chunks
        Uses processed_text (document + OCR text) when available
        
        Args:
            chunks: List of retrieved chunks (can include both text chunks and images)
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        current_length = 0
        
        # Group items by document for better organization
        docs_items = {}
        for item in chunks:
            doc_id = item['document_id']
            if doc_id not in docs_items:
                docs_items[doc_id] = []
            docs_items[doc_id].append(item)
        
        # Format context by document
        for doc_id, doc_items in docs_items.items():
            # Sort items by index (chunk_index or image_index) for coherent reading
            doc_items.sort(key=lambda x: x.get('chunk_index', x.get('image_index', 0)))
            
            doc_title = doc_items[0]['document_title']
            subject_name = doc_items[0]['subject_name'] or 'General'
            
            # Try to get the processed_text (document text + OCR text) from the document
            try:
                document = Document.objects.get(id=doc_id)
                if document.processed_text and document.processed_text.strip():
                    # Use the enhanced processed_text that includes OCR text
                    doc_header = f"\n--- From: {doc_title} (Subject: {subject_name}) ---\n"
                    processed_content = document.processed_text.strip()
                    
                    # Check if we can fit it
                    total_length = len(doc_header) + len(processed_content)
                    
                    if current_length + total_length > self.max_context_length:
                        # Truncate the processed text to fit
                        available_space = self.max_context_length - current_length - len(doc_header) - 50
                        if available_space > 200:  # Only add if we have reasonable space
                            context_parts.append(doc_header)
                            context_parts.append(processed_content[:available_space])
                            context_parts.append("\n[Content truncated due to length limit]\n")
                            current_length = self.max_context_length
                        break
                    else:
                        context_parts.append(doc_header)
                        context_parts.append(processed_content + "\n")
                        current_length += total_length
                        continue  # Skip item-based processing for this document
                        
            except Document.DoesNotExist:
                logger.warning(f"Document {doc_id} not found, falling back to items")
            except Exception as e:
                logger.warning(f"Error retrieving processed_text for document {doc_id}: {e}")
            
            # Fallback: Use original item-based approach if processed_text is not available
            doc_header = f"\n--- From: {doc_title} (Subject: {subject_name}) ---\n"
            
            if current_length + len(doc_header) > self.max_context_length:
                break
            
            context_parts.append(doc_header)
            current_length += len(doc_header)
            
            # Add items from this document (chunks or images)
            for item in doc_items:
                item_content = item['content'].strip()
                
                # Add page number if available
                page_info = ""
                if item.get('page_number'):
                    page_info = f"[Page {item['page_number']}] "
                
                item_text = f"{page_info}{item_content}\n"
                
                if current_length + len(item_text) > self.max_context_length:
                    # Add truncation notice
                    context_parts.append("\n[Content truncated due to length limit]\n")
                    break
                
                context_parts.append(item_text)
                current_length += len(item_text)
            
            if current_length >= self.max_context_length:
                break
        
        return "".join(context_parts)
    
    def get_document_summary(self, document_id: str) -> Dict[str, Any]:
        """
        Get a summary of chunks for a specific document
        
        Args:
            document_id: Document ID
            
        Returns:
            Dict with document summary
        """
        try:
            chunks = DocumentChunk.objects.filter(
                document_id=document_id
            ).select_related('document').order_by('chunk_index')
            
            if not chunks.exists():
                return {
                    'success': False,
                    'error': 'Document not found or not processed'
                }
            
            doc = chunks.first().document
            
            # Create summary
            summary = {
                'success': True,
                'document_id': document_id,
                'title': doc.title,
                'document_type': doc.document_type,
                'subject_name': doc.subject.name if doc.subject else None,
                'total_chunks': chunks.count(),
                'total_characters': sum(len(chunk.content) for chunk in chunks),
                'page_count': doc.page_count,
                'processed_at': doc.processed_at.isoformat() if doc.processed_at else None,
                'chunks_summary': []
            }
            
            # Add chunk summaries
            for chunk in chunks[:10]:  # Limit to first 10 chunks
                summary['chunks_summary'].append({
                    'chunk_index': chunk.chunk_index,
                    'content_preview': chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    'page_number': chunk.page_number,
                    'character_count': len(chunk.content)
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting document summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval system statistics"""
        try:
            # Get vector store stats
            vector_stats = self.vector_store.get_stats()
            
            # Add retriever-specific stats
            stats = {
                'vector_store': vector_stats,
                'max_context_length': self.max_context_length,
                'total_subjects': Subject.objects.count(),
                'subjects_with_documents': Subject.objects.filter(
                    documents__processed=True
                ).distinct().count(),
                'retrieval_strategies': ['semantic', 'keyword', 'hybrid']
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting retrieval stats: {e}")
            return {'error': str(e)}
