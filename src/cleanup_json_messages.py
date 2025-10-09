"""
Cleanup script to remove JSON-formatted messages from chat history
Run this with: python manage.py shell < cleanup_json_messages.py
"""

from rag_app.models import ChatMessage
import json

# Find messages that start with JSON-like content
json_messages = ChatMessage.objects.filter(message__startswith='{"success"')

print(f"Found {json_messages.count()} messages with JSON content")

for msg in json_messages:
    try:
        # Try to parse as JSON
        data = json.loads(msg.message)
        
        # Extract the actual response text
        if 'response' in data:
            msg.message = data['response']
            msg.save()
            print(f"✓ Fixed message {msg.id}")
        else:
            print(f"⚠ Message {msg.id} has JSON but no 'response' field")
            
    except json.JSONDecodeError:
        print(f"✗ Message {msg.id} looks like JSON but couldn't parse")

print(f"\nCleanup complete!")
