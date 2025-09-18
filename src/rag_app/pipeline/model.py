"""
Professional RAG Model Integration
Integrates document retrieval with LLM for question answering
"""

import os
import logging
import json
import requests
from typing import Dict, List, Any, Optional
from django.utils import timezone
from dotenv import load_dotenv
from .retriever import DocumentRetriever
from .vectorstore import VectorStore
from ..models import ChatSession, ChatMessage, DocumentChunk, TempDocument

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

logger = logging.getLogger(__name__)


class RAGModelError(Exception):
    """Custom exception for RAG model operations"""
    pass


class RAGModel:
    """
    Professional RAG model for question answering
    
    Features:
    - Document retrieval with multiple strategies
    - LLM integration with OpenRouter
    - Chat history management
    - Subject-specific context
    - Comprehensive error handling
    """
    
    def __init__(self, 
                 embedding_model: str = 'all-MiniLM-L6-v2',
                 llm_model: str = 'openrouter/sonoma-sky-alpha',
                 max_context_length: int = 4000):
        """
        Initialize the RAG model
        
        Args:
            embedding_model: Embedding model for retrieval
            llm_model: LLM model for generation
            max_context_length: Maximum context length
        """
        # Initialize retriever
        self.retriever = DocumentRetriever(embedding_model, max_context_length)
        
        # LLM configuration
        self.llm_model = llm_model
        self.api_key = os.getenv("OPEN_ROUTER_API_KEY")
        
        if not self.api_key:
            raise RAGModelError("OPEN_ROUTER_API_KEY not found in environment variables")
        
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def query(self,
              question: str,
              subject_id: Optional[int] = None,
              chat_session: Optional[ChatSession] = None,
              retrieval_strategy: str = 'hybrid',
              max_chunks: int = 5) -> Dict[str, Any]:
        """
        Process a query using RAG
        
        Args:
            question: User question
            subject_id: Optional subject ID for filtering
            chat_session: Optional chat session for history
            retrieval_strategy: Retrieval strategy to use
            max_chunks: Maximum chunks to retrieve
            
        Returns:
            Dict with answer and metadata
        """
        start_time = timezone.now()
        
        try:
            logger.info(f"Processing RAG query: {question[:50]}...")
            
            # Retrieve relevant documents
            retrieval_result = self.retriever.retrieve_for_query(
                query=question,
                subject_id=subject_id,
                retrieval_strategy=retrieval_strategy,
                max_chunks=max_chunks
            )
            
            if not retrieval_result['success']:
                return {
                    'success': False,
                    'answer': "I couldn't find any relevant documents to answer your question. Please make sure documents are uploaded and processed.",
                    'error': 'No relevant documents found',
                    'metadata': retrieval_result['metadata']
                }
            
            # Build chat messages with context
            messages = self._build_chat_messages(
                question=question,
                context=retrieval_result['context'],
                chat_session=chat_session,
                subject_id=subject_id
            )
            
            # Generate response using LLM
            llm_response = self._generate_llm_response(messages)
            
            if not llm_response['success']:
                return {
                    'success': False,
                    'answer': "I'm sorry, I encountered an error while generating a response. Please try again.",
                    'error': llm_response['error'],
                    'metadata': retrieval_result['metadata']
                }
            
            processing_time = (timezone.now() - start_time).total_seconds()
            
            # Prepare result
            result = {
                'success': True,
                'answer': llm_response['answer'],
                'sources': retrieval_result['chunks'],
                'metadata': {
                    **retrieval_result['metadata'],
                    'llm_model': self.llm_model,
                    'processing_time': processing_time,
                    'tokens_used': llm_response.get('tokens_used'),
                    'response_time': llm_response.get('response_time')
                }
            }
            
            logger.info(f"Successfully processed RAG query in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Error processing RAG query: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'answer': "I apologize, but I encountered an error while processing your question. Please try again.",
                'error': str(e),
                'metadata': {
                    'processing_time': (timezone.now() - start_time).total_seconds()
                }
            }
    
    def chat_with_subject(self,
                         question: str,
                         subject_id: int,
                         chat_session: ChatSession) -> Dict[str, Any]:
        """
        Chat with documents from a specific subject
        
        Args:
            question: User question
            subject_id: Subject ID
            chat_session: Chat session for context
            
        Returns:
            Dict with answer and metadata
        """
        return self.query(
            question=question,
            subject_id=subject_id,
            chat_session=chat_session,
            retrieval_strategy='hybrid'
        )
    
    def query_temp_document(self,
                           question: str,
                           temp_document: 'TempDocument',
                           chat_session: Optional[ChatSession] = None) -> Dict[str, Any]:
        """
        Query a temporary document for anonymous chat
        
        Args:
            question: User question
            temp_document: Temporary document instance
            chat_session: Optional chat session for history
            
        Returns:
            Dict with answer and metadata
        """
        start_time = timezone.now()
        
        try:
            logger.info(f"Processing temp document query: {question[:50]}...")
            
            # Get the actual document content from cache
            from django.core.cache import cache
            cache_key = f"temp_doc_content_{temp_document.id}"
            document_content = cache.get(cache_key)
            
            if not document_content:
                # If not in cache, try to extract again
                from .data_processor import DocumentProcessor
                processor = DocumentProcessor()
                document_content = processor._extract_temp_document_text(temp_document)
                
                # Cache for future use
                cache.set(cache_key, document_content, timeout=86400)  # 24 hours
            
            # Limit context length to avoid token limits
            max_context_length = 8000  # Increased for better content coverage
            if len(document_content) > max_context_length:
                # Take the beginning and end, or use more sophisticated chunking
                document_content = document_content[:max_context_length] + "\n\n[Document content truncated...]"
            
            # Build context with actual document content
            context = f"Document: {temp_document.title}\n\n"
            context += f"Content:\n{document_content}"
            
            # Build messages
            messages = self._build_chat_messages(
                question=question,
                context=context,
                chat_session=chat_session,
                subject_id=None
            )
            
            # Generate response
            llm_response = self._generate_llm_response(messages)
            
            if not llm_response['success']:
                return {
                    'success': False,
                    'answer': "I'm sorry, I encountered an error while processing your question about the document.",
                    'error': llm_response['error']
                }
            
            processing_time = (timezone.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'answer': llm_response['answer'],
                'sources': [{'title': temp_document.title, 'type': 'temp_document'}],
                'metadata': {
                    'temp_document': temp_document.title,
                    'processing_time': processing_time,
                    'llm_model': self.llm_model,
                    'content_length': len(document_content)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in temp document query: {str(e)}")
            return {
                'success': False,
                'answer': "I encountered an error while processing your question about the document.",
                'error': str(e)
            }
    
    def _build_chat_messages(self,
                            question: str,
                            context: str,
                            chat_session: Optional[ChatSession] = None,
                            subject_id: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Build messages for LLM chat completion
        """
        messages = []
        
        # System message with instructions
        system_prompt = self._get_system_prompt(subject_id)
        messages.append({"role": "system", "content": system_prompt})
        
        # Add chat history if available
        if chat_session:
            history_messages = list(ChatMessage.objects.filter(
                session=chat_session
            ).order_by('timestamp'))
            
            # Get last 6 messages (3 exchanges) safely
            if len(history_messages) > 6:
                history_messages = history_messages[-6:]
            
            for msg in history_messages:
                role = "user" if msg.is_user else "assistant"
                messages.append({"role": role, "content": msg.message})
        
        # Add current question with context
        user_message = f"""Context from relevant documents:
{context}

Question: {question}

Please answer based on the provided context. If the context doesn't contain enough information to answer the question, please say so clearly. Do not introduce yourself by name - just provide the educational content directly."""
        
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _get_system_prompt(self, subject_id: Optional[int] = None) -> str:
        """Get system prompt for the LLM"""
        base_prompt = """You are an intelligent educational assistant that helps students learn by answering questions based on their uploaded documents. 

IMPORTANT: Never introduce yourself by name or mention any specific AI assistant names like "Sonoma", "Claude", "GPT", etc. Simply provide helpful educational responses without personal identification.

Your responsibilities:
1. Answer questions accurately based ONLY on the provided document context
2. Clearly indicate when information is not available in the documents
3. Provide detailed explanations when possible
4. Help students understand concepts by breaking down complex topics
5. Suggest related topics they might want to explore
6. Be encouraging and supportive in your responses

Guidelines:
- Always base your answers on the provided context
- If the context is insufficient, clearly state this limitation
- Use clear, educational language appropriate for students
- Provide examples when they help clarify concepts
- Never make up information not in the documents
- Do not introduce yourself by name or mention any specific AI assistant names
- Focus entirely on helping the student understand the content
- Start responses directly with the educational content, not personal introductions"""
        
        if subject_id:
            try:
                from ..models import Subject
                subject = Subject.objects.get(id=subject_id)
                subject_prompt = f"\n\nYou are currently helping with the subject: {subject.name}"
                if subject.description:
                    subject_prompt += f"\nSubject description: {subject.description}"
                base_prompt += subject_prompt
            except:
                pass
        
        return base_prompt
    
    def _generate_llm_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate response using OpenRouter LLM
        """
        try:
            start_time = timezone.now()
            
            payload = {
                "model": self.llm_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4000,  # Further increased for longer responses
                "top_p": 0.9
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60  # Increased timeout for longer responses
            )
            
            response_time = (timezone.now() - start_time).total_seconds()
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"API request failed with status {response.status_code}",
                    'response_time': response_time
                }
            
            response_data = response.json()
            
            # Extract answer
            try:
                answer = response_data["choices"][0]["message"]["content"]
                tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
                
                return {
                    'success': True,
                    'answer': answer,
                    'tokens_used': tokens_used,
                    'response_time': response_time
                }
                
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Response data: {response_data}")
                return {
                    'success': False,
                    'error': f"Error parsing LLM response: {str(e)}",
                    'response_time': response_time
                }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Request timeout - please try again",
                'response_time': 30.0
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}",
                'response_time': 0
            }
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'response_time': 0
            }
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get RAG model statistics"""
        try:
            # Get retrieval stats
            retrieval_stats = self.retriever.get_retrieval_stats()
            
            # Add model-specific stats
            stats = {
                'llm_model': self.llm_model,
                'embedding_model': self.retriever.vector_store.embedding_model_name,
                'max_context_length': self.retriever.max_context_length,
                'api_configured': bool(self.api_key),
                'retrieval_system': retrieval_stats
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting model stats: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear any caches"""
        self.retriever.vector_store.clear_index()
        logger.info("RAG model caches cleared")


# Global RAG model instance
_rag_model = None

def get_rag_model() -> RAGModel:
    """Get or create global RAG model instance"""
    global _rag_model
    if _rag_model is None:
        _rag_model = RAGModel()
    return _rag_model


# Legacy functions for backward compatibility
def rag_query(user_query: str, subject_id: Optional[int] = None) -> str:
    """
    Legacy function for backward compatibility
    """
    try:
        rag_model = get_rag_model()
        result = rag_model.query(user_query, subject_id=subject_id)
        
        if result['success']:
            return result['answer']
        else:
            return f"I apologize, but I encountered an error: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        logger.error(f"Error in legacy rag_query: {e}")
        return "I'm sorry, I encountered an error while processing your question. Please try again."


def update_documents_with_chunks(chunks):
    """
    Legacy function for backward compatibility
    This is now handled by the DocumentProcessor
    """
    logger.warning("update_documents_with_chunks is deprecated. Use DocumentProcessor instead.")
    return len(chunks) if chunks else 0


def get_current_documents():
    """
    Legacy function for backward compatibility
    """
    try:
        from ..models import Document
        return [doc.title for doc in Document.objects.filter(processed=True)]
    except Exception as e:
        logger.error(f"Error getting current documents: {e}")
        return []


def clear_documents():
    """
    Legacy function for backward compatibility
    """
    try:
        rag_model = get_rag_model()
        rag_model.clear_cache()
        logger.info("RAG system cleared")
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")


# Interactive mode (only for testing)
def start_terminal_chat():
    """
    Start an interactive terminal chat session for testing
    """
    print("RAG Chatbot (type 'exit' to quit)")
    
    rag_model = get_rag_model()
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Ending chat.")
            break
        
        try:
            result = rag_model.query(user_input)
            if result['success']:
                print(f"Bot: {result['answer']}")
                if result.get('sources'):
                    print(f"\nSources: {len(result['sources'])} documents")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    start_terminal_chat()