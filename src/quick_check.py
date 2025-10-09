import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.models import DocumentImage, Document

# Quick check
print("Total images:", DocumentImage.objects.count())
print("Total PDF docs:", Document.objects.filter(document_type='pdf').count())

# Check each PDF
for doc in Document.objects.filter(document_type='pdf'):
    img_count = DocumentImage.objects.filter(document=doc).count()
    print(f"  '{doc.title}': {img_count} images")
