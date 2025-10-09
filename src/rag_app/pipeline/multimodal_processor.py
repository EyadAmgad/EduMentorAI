import base64
import io
import os
import logging
from PIL import Image
import requests
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import hashlib
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class MultimodalProcessor:
    """
    Handles image extraction and description for multimodal RAG.
    Integrates with OpenRouter free vision models for educational content analysis.
    """
    
    def __init__(self, openrouter_api_key: str):
        self.api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        # Use Qwen2.5-VL-72B for best educational content understanding
        self.vision_model = os.getenv('VISION_MODEL', 'qwen/qwen2.5-vl-72b-instruct:free')
        self.max_images_per_doc = int(os.getenv('MAX_IMAGES_PER_DOCUMENT', '20'))
        
        # Cache directory for image descriptions
        self.cache_dir = Path('media/cache/image_descriptions')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"MultimodalProcessor initialized with model: {self.vision_model}")
    
    def _get_cache_key(self, image_data: bytes, context: str = "") -> str:
        """Generate cache key for image description"""
        content = image_data + context.encode('utf-8')
        return hashlib.md5(content).hexdigest()
    
    def _get_cached_description(self, cache_key: str) -> Optional[str]:
        """Get cached image description if exists"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('description')
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
        return None
    
    def _save_cached_description(self, cache_key: str, description: str):
        """Save image description to cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'description': description,
                    'timestamp': str(pd.Timestamp.now())
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Error saving to cache file {cache_file}: {e}")
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract images from PDF using PyMuPDF"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"Processing PDF with {len(doc)} pages: {pdf_path}")
            
            for page_num in range(len(doc)):
                if len(images) >= self.max_images_per_doc:
                    logger.info(f"Reached maximum images limit ({self.max_images_per_doc})")
                    break
                    
                page = doc.load_page(page_num)
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    if len(images) >= self.max_images_per_doc:
                        break
                        
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        # Skip if not RGB/RGBA or too small
                        if pix.n - pix.alpha < 4 and pix.width > 50 and pix.height > 50:
                            img_data = pix.tobytes("png")
                            bbox = page.get_image_bbox(img)
                            
                            images.append({
                                'data': img_data,
                                'page': page_num + 1,
                                'index': img_index,
                                'bbox': bbox,
                                'width': pix.width,
                                'height': pix.height,
                                'size_bytes': len(img_data)
                            })
                            
                            logger.debug(f"Extracted image {len(images)} from page {page_num + 1}")
                        
                        pix = None
                    except Exception as e:
                        logger.warning(f"Error extracting image {img_index} from page {page_num + 1}: {e}")
                        continue
            
            doc.close()
            logger.info(f"Extracted {len(images)} images from PDF")
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            
        return images
    
    def extract_images_from_docx(self, docx_path: str) -> List[Dict]:
        """Extract images from DOCX files"""
        images = []
        try:
            from docx import Document
            from docx.document import Document as DocumentType
            
            doc = Document(docx_path)
            logger.info(f"Processing DOCX: {docx_path}")
            
            # Extract images from document relationships
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    if len(images) >= self.max_images_per_doc:
                        break
                        
                    try:
                        img_data = rel.target_part.blob
                        images.append({
                            'data': img_data,
                            'page': 1,  # DOCX doesn't have clear page concept
                            'index': len(images),
                            'size_bytes': len(img_data),
                            'filename': rel.target_ref
                        })
                        logger.debug(f"Extracted image {len(images)} from DOCX")
                    except Exception as e:
                        logger.warning(f"Error extracting image from DOCX: {e}")
                        continue
            
            logger.info(f"Extracted {len(images)} images from DOCX")
            
        except ImportError:
            logger.error("python-docx not installed. Cannot extract images from DOCX.")
        except Exception as e:
            logger.error(f"Error processing DOCX {docx_path}: {e}")
            
        return images
    
    def extract_images_from_pptx(self, pptx_path: str) -> List[Dict]:
        """Extract images from PPTX files"""
        images = []
        try:
            from pptx import Presentation
            
            prs = Presentation(pptx_path)
            logger.info(f"Processing PPTX with {len(prs.slides)} slides: {pptx_path}")
            
            for slide_num, slide in enumerate(prs.slides):
                if len(images) >= self.max_images_per_doc:
                    break
                    
                for shape in slide.shapes:
                    if len(images) >= self.max_images_per_doc:
                        break
                        
                    if hasattr(shape, 'image'):
                        try:
                            img_data = shape.image.blob
                            images.append({
                                'data': img_data,
                                'page': slide_num + 1,
                                'index': len(images),
                                'size_bytes': len(img_data),
                                'slide_title': slide.shapes.title.text if slide.shapes.title else f"Slide {slide_num + 1}"
                            })
                            logger.debug(f"Extracted image {len(images)} from slide {slide_num + 1}")
                        except Exception as e:
                            logger.warning(f"Error extracting image from slide {slide_num + 1}: {e}")
                            continue
            
            logger.info(f"Extracted {len(images)} images from PPTX")
            
        except ImportError:
            logger.error("python-pptx not installed. Cannot extract images from PPTX.")
        except Exception as e:
            logger.error(f"Error processing PPTX {pptx_path}: {e}")
            
        return images
    
    def describe_image(self, image_data: bytes, context: str = "", page_info: str = "") -> str:
        """Convert image to educational description using vision model"""
        
        # Check cache first
        cache_key = self._get_cache_key(image_data, context)
        cached_desc = self._get_cached_description(cache_key)
        if cached_desc:
            logger.debug("Using cached image description")
            return cached_desc
        
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create educational prompt
            prompt = f"""You are analyzing an educational document. Describe this image in detail for learning purposes, focusing on:

1. Any text, formulas, equations, or mathematical expressions visible
2. Charts, graphs, diagrams, tables, and their data/meaning
3. Educational concepts, theories, or principles being illustrated
4. Relationships between visual elements and their significance
5. Any step-by-step processes or workflows shown
6. Scientific, technical, or academic content

Context from surrounding text: {context[:300] if context else 'No context available'}
Page/Location info: {page_info}

Provide a comprehensive, educational description that would help students understand the content and answer questions about it. Be specific about numbers, data, formulas, and key concepts shown."""
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://edumentorai.com",
                    "X-Title": "EduMentorAI Multimodal Processing"
                },
                json={
                    "model": self.vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.2  # Lower temperature for more consistent descriptions
                },
                timeout=30
            )
            
            if response.status_code == 200:
                description = response.json()['choices'][0]['message']['content']
                
                # Cache the description
                self._save_cached_description(cache_key, description)
                
                logger.info("Successfully generated image description")
                return description
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return f"[IMAGE DESCRIPTION UNAVAILABLE - API Error: {response.status_code}]"
                
        except requests.exceptions.Timeout:
            logger.error("Timeout while calling vision model API")
            return "[IMAGE DESCRIPTION UNAVAILABLE - API Timeout]"
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            return f"[IMAGE DESCRIPTION UNAVAILABLE - Error: {str(e)}]"
    
    def process_document_images(self, file_path: str, document_context: str = "") -> List[Dict]:
        """Process all images in a document and return descriptions"""
        file_ext = Path(file_path).suffix.lower()
        images = []
        
        logger.info(f"Processing images from {file_path} (type: {file_ext})")
        
        # Extract images based on file type
        if file_ext == '.pdf':
            images = self.extract_images_from_pdf(file_path)
        elif file_ext == '.docx':
            images = self.extract_images_from_docx(file_path)
        elif file_ext == '.pptx':
            images = self.extract_images_from_pptx(file_path)
        else:
            logger.warning(f"Unsupported file type for image extraction: {file_ext}")
            return []
        
        # Generate descriptions for extracted images
        described_images = []
        for i, img in enumerate(images):
            try:
                page_info = f"Page {img['page']}" if 'page' in img else f"Image {i+1}"
                
                description = self.describe_image(
                    img['data'],
                    context=document_context,
                    page_info=page_info
                )
                
                described_images.append({
                    'page': img.get('page', 1),
                    'index': img.get('index', i),
                    'description': description,
                    'size_bytes': img.get('size_bytes', 0),
                    'width': img.get('width'),
                    'height': img.get('height'),
                    'slide_title': img.get('slide_title', ''),
                    'filename': img.get('filename', ''),
                    'bbox': img.get('bbox')
                })
                
                logger.info(f"Processed image {i+1}/{len(images)} from {page_info}")
                
            except Exception as e:
                logger.error(f"Error processing image {i+1}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(described_images)} images")
        return described_images
