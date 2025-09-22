"""
Quiz Generator Module
Generates quizzes using RAG model and LLM
"""

import logging
import json
from typing import Dict, List, Any, Optional
from .model import get_rag_model
from ..models import Quiz, Question, AnswerChoice, Document, Subject

logger = logging.getLogger(__name__)


class QuizGenerationError(Exception):
    """Custom exception for quiz generation errors"""
    pass


class QuizGenerator:
    """
    Quiz Generator using RAG model and LLM
    
    Generates questions and answer choices based on document content
    using a retrieval-augmented generation approach.
    """
    
    def __init__(self):
        """Initialize quiz generator"""
        self.rag_model = get_rag_model()
        
        # Question generation template
        self.question_generation_template = '''You are an expert at creating educational multiple-choice questions. Generate {num_questions} questions based on the following content. Follow the instructions precisely.

        Instructions:
        1. Create {num_questions} multiple-choice questions that:
           - Test understanding of key concepts
           - Have exactly 4 possible answers
           - Have exactly one correct answer
           - Include a brief explanation
        2. Format your ENTIRE response as a valid JSON object
        3. Include ONLY the JSON object, no other text
        4. Use exactly this JSON structure:
        {{
            "questions": [
                {{
                    "question": "What is the question text?",
                    "choices": [
                        {{"text": "First answer choice", "is_correct": true}},
                        {{"text": "Second answer choice", "is_correct": false}},
                        {{"text": "Third answer choice", "is_correct": false}},
                        {{"text": "Fourth answer choice", "is_correct": false}}
                    ],
                    "explanation": "Explanation of why the correct answer is right"
                }}
            ]
        }}

        Content to base questions on:
        {content}

        Remember: Your entire response must be a single, valid JSON object exactly matching the structure above.
        '''
    
    def generate_quiz(self, subject_id: int, num_questions: int = 10, specific_topics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a complete quiz for a subject
        
        Args:
            subject_id: ID of the subject
            num_questions: Number of questions to generate (max 15)
            specific_topics: Optional list of topics to focus on
            
        Returns:
            Dict with quiz questions and metadata
        """
        try:
            # Validate input
            num_questions = min(max(1, num_questions), 15)
            
            # Get subject documents
            from django.shortcuts import get_object_or_404
            subject = get_object_or_404(Subject, id=subject_id)
            documents = Document.objects.filter(subject=subject, processed=True)
            
            if not documents.exists():
                raise QuizGenerationError(f"No processed documents found for subject: {subject.name}")
            
            # Extract relevant content for questions
            question_content = self._extract_content_for_questions(documents, specific_topics)
            
            # Generate questions using RAG
            questions = self._generate_questions(question_content, num_questions)
            
            return {
                'success': True,
                'questions': questions,
                'metadata': {
                    'subject': subject.name,
                    'num_questions': len(questions),
                    'topics': specific_topics or ['general'],
                    'sources': [doc.title for doc in documents]
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating quiz: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_content_for_questions(self, documents: List[Document], topics: Optional[List[str]] = None) -> str:
        """
        Extract relevant content from documents for generating questions
        
        Args:
            documents: List of Document objects
            topics: Optional list of specific topics
            
        Returns:
            String of relevant content
        """
        content = ""
        
        try:
            # Get chunks from documents
            for doc in documents:
                # If topics specified, try to find relevant chunks
                if topics:
                    topic_string = " ".join(topics)
                    chunks = doc.chunks.all()
                    # Simple relevance check (can be enhanced)
                    relevant_chunks = [
                        chunk for chunk in chunks
                        if any(topic.lower() in chunk.content.lower() for topic in topics)
                    ]
                    if relevant_chunks:
                        content += "\n\n" + "\n".join(chunk.content for chunk in relevant_chunks)
                else:
                    # Take a sample of chunks if no specific topics
                    chunks = doc.chunks.all()[:5]  # Limit to 5 chunks per document
                    content += "\n\n" + "\n".join(chunk.content for chunk in chunks)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            raise QuizGenerationError("Failed to extract content from documents")
    
    def _generate_questions(self, content: str, num_questions: int) -> List[Dict[str, Any]]:
        """
        Generate questions using RAG model
        
        Args:
            content: Document content to base questions on
            num_questions: Number of questions to generate
            
        Returns:
            List of question dictionaries
        """
        try:
            # Create prompt for question generation
            prompt = self.question_generation_template.format(
                num_questions=num_questions,
                content=content[:4000]  # Limit content length for prompt
            )
            
            # Call RAG model's LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert educational quiz generator. Create clear, accurate multiple-choice questions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self.rag_model._generate_llm_response(messages)
            
            if not response['success']:
                raise QuizGenerationError(f"LLM response failed: {response.get('error')}")
            
            # Parse the JSON response
            try:
                # Log the raw response for debugging
                logger.debug(f"Raw LLM response: {response['answer']}")
                
                # Try to clean the response - remove any leading/trailing whitespace and non-JSON text
                clean_response = response['answer'].strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()
                
                # Log the cleaned response
                logger.debug(f"Cleaned response: {clean_response}")
                
                # Parse JSON
                result = json.loads(clean_response)
                questions = result.get('questions', [])
                
                if not questions:
                    logger.error("No questions found in response")
                    raise QuizGenerationError("Generated response contained no questions")
                
                # Validate questions
                validated_questions = []
                for i, q in enumerate(questions):
                    if self._validate_question(q):
                        validated_questions.append(q)
                    else:
                        logger.warning(f"Question {i+1} failed validation: {q}")
                
                if not validated_questions:
                    raise QuizGenerationError("No valid questions were generated")
                
                return validated_questions
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {str(e)}\nResponse was: {response['answer']}")
                raise QuizGenerationError("Failed to parse generated questions - invalid JSON format")
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise QuizGenerationError(f"Question generation failed: {str(e)}")
    
    def _validate_question(self, question: Dict[str, Any]) -> bool:
        """
        Validate a generated question
        
        Args:
            question: Question dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['question', 'choices', 'explanation']
            if not all(field in question for field in required_fields):
                return False
            
            # Validate choices
            choices = question['choices']
            if not isinstance(choices, list) or len(choices) != 4:
                return False
            
            # Check choices have required fields and exactly one correct answer
            correct_count = 0
            for choice in choices:
                if not isinstance(choice, dict):
                    return False
                if 'text' not in choice or 'is_correct' not in choice:
                    return False
                if choice['is_correct']:
                    correct_count += 1
            
            return correct_count == 1
            
        except Exception:
            return False
    
    def save_quiz(self, subject_id: int, title: str, questions: List[Dict[str, Any]], 
                 created_by_id: int, description: str = "") -> Quiz:
        """
        Save generated quiz to database
        
        Args:
            subject_id: Subject ID
            title: Quiz title
            questions: List of question dictionaries
            created_by_id: User ID of creator
            description: Optional quiz description
            
        Returns:
            Created Quiz object
        """
        try:
            # Create quiz
            quiz = Quiz.objects.create(
                subject_id=subject_id,
                title=title,
                created_by_id=created_by_id,
                description=description,
                total_questions=len(questions)
            )
            
            # Create questions and choices
            for i, q_data in enumerate(questions, 1):
                question = Question.objects.create(
                    quiz=quiz,
                    question_text=q_data['question'],
                    question_type='mcq',  # Currently only supporting MCQ
                    explanation=q_data['explanation'],
                    order=i
                )
                
                # Create choices
                for j, choice_data in enumerate(q_data['choices'], 1):
                    AnswerChoice.objects.create(
                        question=question,
                        choice_text=choice_data['text'],
                        is_correct=choice_data['is_correct'],
                        order=j
                    )
            
            return quiz
            
        except Exception as e:
            logger.error(f"Error saving quiz: {str(e)}")
            raise QuizGenerationError(f"Failed to save quiz: {str(e)}")
    
    def generate_google_form_content(self, questions: List[Dict[str, Any]]) -> str:
        """
        Generate content for Google Form
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            String with formatted questions and choices
        """
        form_content = []
        
        for i, question in enumerate(questions, 1):
            # Add question
            form_content.append(f"{i}. {question['question']}")
            
            # Add choices
            for j, choice in enumerate(question['choices'], ord('a')):
                form_content.append(f"   {chr(j)}. {choice['text']}")
            
            form_content.append("")  # Add blank line between questions
        
        return "\n".join(form_content)
