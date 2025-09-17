from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
import os
from dotenv import load_dotenv
import json
import requests
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Global variables to store only uploaded documents and embeddings
uploaded_documents = []
model_embeddings = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize empty FAISS index (will be populated when documents are uploaded)
index = None

def update_documents_with_chunks(chunks):
    """
    Update the document store and FAISS index with new chunks from uploaded files
    Args:
        chunks: List of Document objects from langchain text splitter
    """
    global uploaded_documents, index
    
    # Extract text content from chunks
    new_documents = [chunk.page_content for chunk in chunks]
    
    # Add to our uploaded documents store
    uploaded_documents.extend(new_documents)
    
    # Create/recreate FAISS index with all uploaded documents
    if uploaded_documents:
        all_embeddings = model_embeddings.encode(uploaded_documents, convert_to_tensor=True)
        
        # Create new FAISS index
        index = faiss.IndexFlatL2(all_embeddings.shape[1])
        index.add(np.array(all_embeddings))
    
    return len(new_documents)

def get_current_documents():
    """Get all current uploaded documents"""
    return uploaded_documents

def clear_documents():
    """Clear all uploaded documents (useful for testing or reset)"""
    global uploaded_documents, index
    uploaded_documents = []
    index = None

# OpenRouter Setup
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
if(not OPENROUTER_API_KEY):
    raise ValueError("OPEN_ROUTER_API_KEY not found in environment variables.")
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

# Chat History 
chat_history = []  # Will store conversation turns

def rag_query(user_query):
    # Check if we have any uploaded documents
    if not uploaded_documents or index is None:
        return "No documents have been uploaded yet. Please upload some documents first to ask questions."
    
    # 1. Retrieve relevant chunks
    query_embedding = model_embeddings.encode([user_query])
    D, I = index.search(query_embedding, k=3)
    
    # Get all current uploaded documents
    retrieved_chunks = [uploaded_documents[i] for i in I[0]]
    retrieved_context = "\n".join(retrieved_chunks)

    # 2. Build messages for OpenRouter
    messages = [{"role": "system", "content": "You are a helpful assistant. Answer questions based only on the provided context from uploaded documents."}]
    messages.extend(chat_history)  # add previous conversation
    messages.append({
        "role": "user",
        "content": f"Context from uploaded documents:\n{retrieved_context}\n\nQuestion: {user_query}"
    })

    # 3. Send request to OpenRouter
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",  # set your API key
            "Content-Type": "application/json",
   # optional, replace with your app name
        },
        data=json.dumps({
            "model": "openrouter/sonoma-sky-alpha",  # ⚠️ must be a valid model in your account
            "messages": messages,
        })
    )

    # 4. Parse response
    answer_json = response.json()
    try:
        answer = answer_json["choices"][0]["message"]["content"]
    except Exception:
        answer = f"Error: {answer_json}"

    # 5. Save this turn into history
    chat_history.append({"role": "user", "content": user_query})
    chat_history.append({"role": "assistant", "content": answer})

    return answer



# ==== Step 4: Interactive Loop ====
def start_terminal_chat():
    """
    Start an interactive terminal chat session.
    This is now optional and won't run automatically.
    """
    print("RAG Chatbot with Memory (type 'exit' to quit)")
    
    user_input = input("You: ")
    
    answer = rag_query(user_input)
    print(f"Bot: {answer}\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Ending chat.")
            break
        try:
            answer = rag_query(user_input)
            print(f"Bot: {answer}\n")
        except Exception as e:
            print("Error:", e)


# Only run interactive mode if this file is executed directly (not imported)
if __name__ == "__main__":
    start_terminal_chat()