# Multimodal RAG Features for EduMentorAI

## Overview

EduMentorAI now supports **multimodal RAG** capabilities, enabling the system to understand and process images within documents alongside text content. This enhancement allows students and educators to interact with visual content like charts, diagrams, formulas, and illustrations through AI-powered conversations.

## 🌟 New Capabilities

### Image Understanding
- **Extract images from PDFs, DOCX, and PPTX files**
- **Generate detailed educational descriptions** of visual content
- **Understand charts, graphs, diagrams, and mathematical formulas**
- **Process scientific illustrations and technical drawings**
- **Analyze text within images** (OCR-like functionality)

### Enhanced RAG Responses
- **Answer questions about visual content** in documents
- **Reference specific charts or diagrams** in conversations
- **Provide explanations of complex visual concepts**
- **Generate quizzes based on visual content**
- **Maintain context between text and image content**

### Intelligent Processing
- **Automatic image extraction** during document upload
- **Smart caching** of image descriptions to reduce API costs
- **Page-aware processing** linking images to their document locations
- **Contextual descriptions** using surrounding text for better understanding

## 🔧 Technical Implementation

### Architecture

The multimodal system uses an **image-to-text conversion approach** that:
1. Extracts images from uploaded documents
2. Converts images to detailed text descriptions using vision models
3. Integrates descriptions into the existing text-based RAG pipeline
4. Maintains compatibility with current embedding and retrieval systems

### Vision Models

Integrates with **OpenRouter free vision models**:
- **Primary**: `qwen/qwen2.5-vl-72b-instruct:free` (131K context, excellent for educational content)
- **Alternative**: `google/gemini-2.0-flash-exp:free` (1.05M context, fast processing)
- **Fallback**: Other Qwen2.5-VL and Gemma 3 models

### File Support

| File Type | Text Extraction | Image Extraction | Status |
|-----------|----------------|------------------|--------|
| PDF | ✅ PyMuPDF/PyPDF2 | ✅ PyMuPDF | Ready |
| DOCX | ✅ python-docx | ✅ python-docx | Ready |
| PPTX | ✅ python-pptx | ✅ python-pptx | Ready |
| TXT | ✅ Native | ❌ N/A | Ready |

## 🚀 Setup and Configuration

### Environment Variables

Add these settings to your `.env` file:

```bash
# Enable multimodal processing
ENABLE_MULTIMODAL=True

# Vision model selection (free models)
VISION_MODEL=qwen/qwen2.5-vl-72b-instruct:free

# Processing limits
MAX_IMAGES_PER_DOCUMENT=20

# OpenRouter API key (required for vision models)
OPEN_ROUTER_API_KEY=your-openrouter-api-key
```

### Installation

1. **Update dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **New dependencies added**:
   - `Pillow>=10.0.0` - Image processing
   - `pandas>=1.5.0` - Data handling (required for caching)

3. **Run migrations** (if any database changes):
   ```bash
   python manage.py migrate
   ```

### Directory Structure

The system creates these new directories:
```
media/
└── cache/
    └── image_descriptions/  # Cached image descriptions
```

## 📖 Usage Guide

### For Students

1. **Upload Documents with Images**
   - Upload PDFs, DOCX, or PPTX files containing charts, diagrams, or illustrations
   - The system automatically detects and processes images during upload
   - Processing time increases based on number of images (typically 10-30 seconds per image)

2. **Chat with Visual Content**
   ```
   User: "What does the graph on page 3 show?"
   AI: "The graph on page 3 shows the relationship between temperature and enzyme activity..."
   
   User: "Explain the diagram in slide 5"
   AI: "The diagram in slide 5 illustrates the process of photosynthesis..."
   ```

3. **Generate Visual Quizzes**
   - Create quizzes that include questions about charts, graphs, and diagrams
   - Questions automatically reference visual content in the documents

### For Developers

#### Processing Pipeline

```python
from rag_app.pipeline.data_processor import DocumentProcessor

# Initialize with multimodal support
processor = DocumentProcessor()

# Process document (automatically handles images if enabled)
result = processor.process_document(document)

print(f"Images processed: {result['images_processed']}")
print(f"Total chunks: {result['chunks_created']}")
```

#### Direct Image Processing

```python
from rag_app.pipeline.multimodal_processor import MultimodalProcessor

# Initialize processor
processor = MultimodalProcessor(api_key="your-key")

# Process images from a document
image_descriptions = processor.process_document_images(
    file_path="/path/to/document.pdf",
    document_context="Course material on biology..."
)

for img_desc in image_descriptions:
    print(f"Page {img_desc['page']}: {img_desc['description']}")
```

## 💰 Cost Optimization

### Free Tier Friendly
- **Uses only free OpenRouter models** - no additional API costs
- **Intelligent caching** - processes each unique image only once
- **Rate limit aware** - respects OpenRouter free tier limits
- **Resource efficient** - works within Hugging Face Spaces constraints

### Cache Management
- Image descriptions are cached using MD5 hashes
- Cache files stored in `media/cache/image_descriptions/`
- Automatic cache cleanup (configurable)
- Reduces processing time for repeated uploads

## 📊 Performance Metrics

### Processing Times
- **Text-only documents**: Same as before (~5-15 seconds)
- **Documents with images**: +10-30 seconds per image
- **Cached images**: Near-instant processing

### Resource Usage
- **Memory**: Minimal increase (images processed sequentially)
- **Storage**: ~50-200KB per image description
- **API calls**: 1 call per unique image

### Accuracy
- **Educational content**: Excellent (Qwen2.5-VL optimized for educational materials)
- **Mathematical formulas**: Very good recognition and explanation
- **Charts/graphs**: High accuracy in data interpretation
- **Diagrams**: Good understanding of relationships and processes

## 🛠 Troubleshooting

### Common Issues

1. **"No images found in document"**
   - Verify document contains extractable images
   - Check if images are embedded vs. linked
   - Ensure file format is supported

2. **"API Error" in image descriptions**
   - Verify `OPEN_ROUTER_API_KEY` is set correctly
   - Check OpenRouter API rate limits
   - Ensure vision model is available

3. **Processing takes too long**
   - Reduce `MAX_IMAGES_PER_DOCUMENT` setting
   - Check image cache for duplicates
   - Consider using faster vision model

### Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger('rag_app.pipeline.multimodal_processor').setLevel(logging.DEBUG)
```

### Health Check

```python
from rag_app.pipeline.data_processor import DocumentProcessor

processor = DocumentProcessor()
stats = processor.get_processing_stats()

print(f"Multimodal enabled: {stats['multimodal_enabled']}")
print(f"Image description chunks: {stats.get('image_description_chunks', 0)}")
```

## 🔮 Future Enhancements

### Planned Features
- **True multimodal embeddings** (CLIP-based)
- **Image similarity search**
- **Visual question answering with image display**
- **Automatic figure/table numbering**
- **Math equation LaTeX conversion**

### Integration Opportunities
- **Diagram generation** from text descriptions
- **Image annotation** and highlighting
- **Visual answer validation** for quizzes
- **Accessibility features** for visually impaired users

## 📝 API Documentation

### MultimodalProcessor Class

```python
class MultimodalProcessor:
    def __init__(self, openrouter_api_key: str)
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]
    def extract_images_from_docx(self, docx_path: str) -> List[Dict]
    def extract_images_from_pptx(self, pptx_path: str) -> List[Dict]
    def describe_image(self, image_data: bytes, context: str = "", page_info: str = "") -> str
    def process_document_images(self, file_path: str, document_context: str = "") -> List[Dict]
```

### Enhanced DocumentProcessor

```python
class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, embedding_model: str = 'all-MiniLM-L6-v2')
    def process_document(self, document: DocumentModel) -> Dict[str, Any]  # Now includes image processing
    def process_temp_document(self, temp_doc) -> Dict[str, Any]  # Now supports images
```

## 🤝 Contributing

When contributing to multimodal features:

1. **Test with various document types** (PDF, DOCX, PPTX)
2. **Include sample documents with images** in tests
3. **Consider resource constraints** (Hugging Face Spaces limits)
4. **Optimize for free tier usage** (OpenRouter limits)
5. **Document performance implications**

## 📄 License

Multimodal features are included under the same MIT License as the main project.

---

**Built with ❤️ by the EduMentorAI Team**

*Transforming education through multimodal artificial intelligence*