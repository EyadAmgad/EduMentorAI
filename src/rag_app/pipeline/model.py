from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
from data import documents
import os
from dotenv import load_dotenv
import json
import requests
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))
# Embeddings + FAISS Setup 
model_embeddings = SentenceTransformer('all-MiniLM-L6-v2')
doc_embeddings = model_embeddings.encode(documents, convert_to_tensor=True)

index = faiss.IndexFlatL2(doc_embeddings.shape[1])
index.add(np.array(doc_embeddings))

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
    # 1. Retrieve relevant chunks
    query_embedding = model_embeddings.encode([user_query])
    D, I = index.search(query_embedding, k=3)
    retrieved_chunks = [documents[i] for i in I[0]]
    retrieved_context = "\n".join(retrieved_chunks)

    # 2. Build messages for OpenRouter
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    messages.extend(chat_history)  # add previous conversation
    messages.append({
        "role": "user",
        "content": f"Context:\n{retrieved_context}\n\nQuestion: {user_query}"
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
            "model": "google/gemini-2.5-flash-image-preview:free",  # ⚠️ must be a valid model in your account
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
