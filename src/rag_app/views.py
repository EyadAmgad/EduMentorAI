from django.shortcuts import render
from .models import Document
from .forms import DocumentForm
from django.http import JsonResponse
from controllers.ProcessController import ProcessController
from controllers.ProjectController import ProjectController
from .pipeline.model import update_documents_with_chunks, rag_query, get_current_documents
import os
import uuid
# Create your views here.
def index(request):
    if request.method == "POST":
        title = request.POST.get("title")
        file = request.FILES.get("file")

        if not title or not file:
            return JsonResponse({"error": "Title and file required"}, status=400)

        try:
            # Create document in database
            doc = Document.objects.create(title=title, file=file)
            
            # Generate a unique project ID for this document
            project_id = str(uuid.uuid4())
            
            # Get the project path and copy the file there for processing
            project_controller = ProjectController()
            project_path = project_controller.get_project_path(project_id)
            
            # Copy the uploaded file to the project directory
            source_file_path = doc.file.path
            filename = os.path.basename(source_file_path)
            destination_file_path = os.path.join(project_path, filename)
            
            # Copy file content
            with open(source_file_path, 'rb') as source:
                with open(destination_file_path, 'wb') as destination:
                    destination.write(source.read())
            
            # Process the file using ProcessController
            process_controller = ProcessController(project_id)
            
            # Get file content
            file_content = process_controller.get_file_content(filename)
            
            if not file_content:
                return JsonResponse({"error": "Unsupported file type. Only PDF and TXT files are supported."}, status=400)
            
            # Process file content into chunks
            chunks = process_controller.process_file_content(file_content)
            
            # Update the pipeline model with new chunks
            chunks_added = update_documents_with_chunks(chunks)
            
            # Get total document count after adding
            total_documents = len(get_current_documents())
            
            return JsonResponse({
                "message": "Document uploaded, processed, and added to knowledge base successfully", 
                "id": doc.id,
                "project_id": project_id,
                "chunks_count": len(chunks),
                "chunks_added_to_pipeline": chunks_added,
                "total_documents_in_knowledge_base": total_documents,
                "filename": filename
            })
            
        except Exception as e:
            return JsonResponse({"error": f"Error processing file: {str(e)}"}, status=500)
            
    # For GET requests, also return current document count
    total_documents = len(get_current_documents())
    context = {'total_documents': total_documents}
    return render(request, 'rag_app/index.html', context)

def chatbot(request):
    """
    Render the chatbot interface
    """
    total_documents = len(get_current_documents())
    uploaded_docs = Document.objects.all().order_by('-id')[:5]  # Show last 5 uploaded docs
    context = {
        'total_documents': total_documents,
        'uploaded_docs': uploaded_docs
    }
    return render(request, 'rag_app/chatbot.html', context)

def query_rag(request):
    """
    Handle RAG queries using only the uploaded documents
    """
    if request.method == "POST":
        # Debug: Print all POST data
        print(f"POST data: {dict(request.POST)}")
        print(f"Content type: {request.content_type}")
        
        user_query = request.POST.get("query")
        
        # Debug logging
        print(f"Received POST request with data: {request.POST}")
        print(f"Query extracted: '{user_query}'")
        
        if not user_query or user_query.strip() == "":
            return JsonResponse({"error": "Query is required and cannot be empty"}, status=400)
        
        try:
            # Check if we have documents first
            current_docs = get_current_documents()
            if not current_docs:
                return JsonResponse({
                    "query": user_query,
                    "answer": "No documents have been uploaded yet. Please upload some documents first to ask questions.",
                    "total_documents_used": 0,
                    "status": "success"
                })
            
            # Get answer from RAG system (only from uploaded documents)
            answer = rag_query(user_query.strip())
            
            return JsonResponse({
                "query": user_query,
                "answer": answer,
                "total_documents_used": len(current_docs),
                "status": "success"
            })
            
        except Exception as e:
            print(f"Error in query_rag: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Error processing query: {str(e)}"}, status=500)
    
    return JsonResponse({"error": "Only POST method allowed"}, status=405)