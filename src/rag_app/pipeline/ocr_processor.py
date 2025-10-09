"""
OCR Text Extraction for Images in Documents
Handles image extraction from PDFs and OCR text extraction using EasyOCR
"""

import logging
import easyocr
from pathlib import Path
from PIL import Image
import io
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Tuple
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Professional OCR processor for extracting text from images
    
    Features:
    - EasyOCR integration for text extraction
    - Multiple language support
    - Image preprocessing for better OCR results
    - Batch processing support
    """
    
    def __init__(self, languages: List[str] = None):
        """
        Initialize OCR processor
        
        Args:
            languages: List of language codes (default: ['en'])
        """
        self.languages = languages or ['en']
        self.reader = None
        self._initialize_reader()
    
    def _initialize_reader(self):
        """Initialize EasyOCR reader"""
        try:
            logger.info(f"Initializing EasyOCR reader with languages: {self.languages}")
            self.reader = easyocr.Reader(self.languages, gpu=False)  # Set gpu=True if CUDA is available
            logger.info("EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {e}")
            raise
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from a single image file using EasyOCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            if not self.reader:
                self._initialize_reader()
            
            results = self.reader.readtext(str(image_path))
            text = " ".join([res[1] for res in results])
            
            logger.info(f"Extracted {len(text)} characters from {image_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            return ""
    
    def extract_text_from_images(self, image_paths: List[str]) -> str:
        """
        Extract text from multiple image files using EasyOCR
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            Combined extracted text from all images
        """
        try:
            all_text = []
            
            for img_path in image_paths:
                text = self.extract_text_from_image(img_path)
                if text:
                    all_text.append(text)
            
            combined_text = "\n".join(all_text)
            logger.info(f"Extracted text from {len(image_paths)} images, total {len(combined_text)} characters")
            
            return combined_text
            
        except Exception as e:
            logger.error(f"Error extracting text from multiple images: {e}")
            return ""
    
    def extract_text_from_pil_image(self, pil_image: Image.Image) -> str:
        """
        Extract text from a PIL Image object
        
        Args:
            pil_image: PIL Image object
            
        Returns:
            Extracted text from the image
        """
        try:
            if not self.reader:
                self._initialize_reader()
            
            # Convert PIL image to numpy array for easyocr
            import numpy as np
            image_array = np.array(pil_image)
            
            results = self.reader.readtext(image_array)
            text = " ".join([res[1] for res in results])
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PIL image: {e}")
            return ""


class PDFImageExtractor:
    """
    Extract images from PDF documents
    
    Features:
    - Image extraction from PDFs using PyMuPDF
    - Image preprocessing and optimization
    - Metadata extraction
    """
    
    def __init__(self, min_width: int = 100, min_height: int = 100):
        """
        Initialize PDF image extractor
        
        Args:
            min_width: Minimum image width to extract
            min_height: Minimum image height to extract
        """
        self.min_width = min_width
        self.min_height = min_height
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract all images from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dicts containing image data and metadata
        """
        try:
            pdf_document = fitz.open(pdf_path)
            extracted_images = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        
                        if not base_image:
                            continue
                        
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)
                        
                        # Filter out small images
                        if width < self.min_width or height < self.min_height:
                            continue
                        
                        # Convert to PIL Image
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Convert CMYK to RGB if necessary
                        if pil_image.mode == 'CMYK':
                            pil_image = pil_image.convert('RGB')
                        
                        # Save to bytes buffer
                        buffer = io.BytesIO()
                        save_format = 'PNG' if image_ext.upper() not in ['JPEG', 'JPG'] else 'JPEG'
                        pil_image.save(buffer, format=save_format)
                        buffer.seek(0)
                        
                        extracted_images.append({
                            'page_number': page_num + 1,
                            'image_index': img_index,
                            'image_bytes': buffer.getvalue(),
                            'format': save_format.lower(),
                            'width': width,
                            'height': height,
                            'pil_image': pil_image
                        })
                        
                        logger.info(f"Extracted image {img_index} from page {page_num + 1} ({width}x{height})")
                        
                    except Exception as e:
                        logger.error(f"Error extracting image {img_index} from page {page_num}: {e}")
                        continue
            
            pdf_document.close()
            logger.info(f"Extracted {len(extracted_images)} images from {pdf_path}")
            
            return extracted_images
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF {pdf_path}: {e}")
            return []
    
    def extract_images_with_ocr(self, pdf_path: str, ocr_processor: OCRProcessor) -> List[Dict[str, Any]]:
        """
        Extract images from PDF and perform OCR on them
        
        Args:
            pdf_path: Path to the PDF file
            ocr_processor: OCRProcessor instance for text extraction
            
        Returns:
            List of dicts containing image data, metadata, and OCR text
        """
        try:
            extracted_images = self.extract_images_from_pdf(pdf_path)
            
            for img_data in extracted_images:
                try:
                    # Extract OCR text from PIL image
                    ocr_text = ocr_processor.extract_text_from_pil_image(img_data['pil_image'])
                    img_data['ocr_text'] = ocr_text
                    img_data['has_text'] = len(ocr_text.strip()) > 0
                    
                    logger.info(f"OCR extracted {len(ocr_text)} characters from image on page {img_data['page_number']}")
                    
                except Exception as e:
                    logger.error(f"Error performing OCR on image: {e}")
                    img_data['ocr_text'] = ""
                    img_data['has_text'] = False
            
            return extracted_images
            
        except Exception as e:
            logger.error(f"Error extracting images with OCR: {e}")
            return []


def extract_images_and_ocr_from_pdf(pdf_path: str, languages: List[str] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to extract images and OCR text from a PDF
    
    Args:
        pdf_path: Path to the PDF file
        languages: List of language codes for OCR (default: ['en'])
        
    Returns:
        List of dicts containing image data and OCR text
    """
    ocr_processor = OCRProcessor(languages=languages)
    image_extractor = PDFImageExtractor()
    
    return image_extractor.extract_images_with_ocr(pdf_path, ocr_processor)
