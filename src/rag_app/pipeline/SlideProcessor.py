import logging
import re
import os
from io import BytesIO

logger = logging.getLogger(__name__)


class SlideProcessor:
    """Advanced helper class for processing documents and generating PowerPoint slides with existing RAG LLM"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx']
        # Initialize the existing RAG model
        try:
            from .model import RAGModel
            self.rag_model = RAGModel()
            self.llm_available = True
        except Exception as e:
            logger.warning(f"Could not initialize RAG model: {str(e)}")
            self.rag_model = None
            self.llm_available = False
    
    def generate_slides(self, files, slide_count, template, title, language, instructions, user, background_image=None, documents=None):
        """
        Main method to generate PowerPoint slides from uploaded documents using existing RAG LLM
        
        Args:
            files: List of file objects or Document model instances
            documents: List of Document model instances (optional, for image support)
            ...
        """
        try:
            # Step 1: Validate and process uploaded files
            processed_content = self._process_uploaded_files(files, documents)
            if not processed_content:
                return {'success': False, 'error': 'No valid content found in uploaded files'}
            
            # Step 1b: Extract images from documents if available
            document_images = []
            if documents:
                document_images = self._extract_document_images(documents)
                logger.info(f"Found {len(document_images)} images across {len(documents)} documents")
            
            # Step 2: Extract and structure content (including image OCR text)
            structured_content = self._extract_content_structure(processed_content, document_images)
            
            # Step 3: Generate slide content using existing RAG LLM (with image awareness)
            if self.llm_available and self.rag_model:
                slide_content_text, image_placements = self._generate_ai_slide_content_with_rag(
                    structured_content, slide_count, instructions, language, title, document_images
                )
            else:
                # Fallback to basic generation
                slide_content_text = self._generate_basic_slide_content(
                    structured_content, slide_count, instructions, language, title
                )
                image_placements = []
            
            # Step 4: Create PowerPoint presentation with advanced styling and images
            presentation_path = self._create_advanced_powerpoint(
                slide_content_text, template, title, user, background_image, image_placements, document_images
            )
            
            # Step 5: Return success response with download URL
            from django.urls import reverse
            download_url = reverse('rag_app:slide_download', kwargs={'filename': presentation_path})
            
            return {
                'success': True,
                'download_url': download_url,
                'file_name': presentation_path,  # Return the actual filename
                'images_included': len(image_placements)
            }
            
        except Exception as e:
            logger.error(f"Error in slide generation: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _sanitize_text(self, text):
        try:
            if not isinstance(text, str):
                text = str(text)
            text = re.sub(r"[\ud800-\udfff]", "", text)
            text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            return text
        except Exception:
            return ''
    
    def _extract_document_images(self, documents):
        """
        Extract images with OCR text from Document model instances
        
        Args:
            documents: List of Document model instances
            
        Returns:
            List of image data dicts with OCR text and metadata
        """
        from ..models import DocumentImage
        import logging
        logger = logging.getLogger(__name__)
        
        all_images = []
        
        for doc in documents:
            try:
                # Get images for this document
                images = DocumentImage.objects.filter(
                    document=doc,
                    ocr_processed=True
                ).order_by('page_number', 'image_index')
                
                for img in images:
                    image_data = {
                        'id': img.id,
                        'document_title': doc.title,
                        'document_id': doc.id,
                        'page_number': img.page_number,
                        'image_index': img.image_index,
                        'ocr_text': img.ocr_text,
                        'image_path': img.image_file.path if img.image_file else None,
                        'width': img.width,
                        'height': img.height
                    }
                    all_images.append(image_data)
                    
                logger.info(f"Extracted {len(images)} images from document '{doc.title}'")
                    
            except Exception as e:
                logger.warning(f"Error extracting images from document {doc.id}: {e}")
                continue
        
        return all_images
    
    def _generate_ai_slide_content_with_rag(self, structured_content, slide_count, instructions, language, title, document_images=[]):
        """Generate slide content using the existing RAG model LLM with image awareness"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Prepare the content for AI processing
            content_summary = structured_content['full_text'][:8000]  # Limit content length
            
            # Determine slide count
            if slide_count == 'auto':
                slide_count = min(max(3, len(structured_content['sections'])), 10)
            
            # Build image context for the LLM
            image_context = ""
            if document_images:
                image_context = "\n\nAVAILABLE IMAGES IN DOCUMENTS:\n"
                for idx, img in enumerate(document_images, 1):
                    ocr_preview = img['ocr_text'][:200] if img['ocr_text'] else "No OCR text"
                    image_context += f"Image {idx} (from page {img['page_number']}): {ocr_preview}\n"
                image_context += f"\nYou have {len(document_images)} images available. When creating slides, if an image's content is relevant to a slide topic, include [IMAGE_{idx}] in that slide's bullet points to indicate where the image should be placed.\n"
            
            # Create the prompt for the LLM
            prompt = f"""
Create exactly {slide_count} slides based on the following document content. 

Document Content:
{content_summary}
{image_context}

Requirements:
- Language: {language}
- Presentation Title: {title or 'Document Analysis'}
- Additional Instructions: {instructions}
- Each slide should have a clear title and 4-6 bullet points
- Make the content educational and well-structured
- Focus on key concepts and important information
- If relevant images are available, include [IMAGE_n] marker in bullet points where the image should appear

Format each slide exactly like this:
### Slide Title Here
• First bullet point
• Second bullet point
• Third bullet point
• [IMAGE_2] (only if relevant image exists)

Please create engaging, informative slides that capture the essence of the document.
Start with a title slide, then create content slides, and end with a summary if appropriate.
"""
            
            # Use the existing RAG model's LLM method
            system_message = "You are an expert educational content creator that creates well-structured, engaging presentation slides with visual elements."
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Call the existing LLM method
            response = self.rag_model._generate_llm_response(messages)
            
            if response['success']:
                slide_text = response['answer']
                # Extract image placements from the generated content
                image_placements = self._extract_image_placements(slide_text, document_images)
                return slide_text, image_placements
            else:
                logger.error(f"LLM generation failed: {response.get('error', 'Unknown error')}")
                # Fallback to basic generation
                return self._generate_basic_slide_content(structured_content, slide_count, instructions, language, title), []
            
        except Exception as e:
            logger.error(f"Error in RAG slide generation: {str(e)}")
            # Fallback to basic generation
            return self._generate_basic_slide_content(structured_content, slide_count, instructions, language, title), []
    
    def _extract_image_placements(self, slide_text, document_images):
        """
        Extract image placement markers from slide text
        
        Returns:
            List of dicts: [{'slide_index': 0, 'image_id': 123, 'image_path': '...'}]
        """
        import re
        import logging
        logger = logging.getLogger(__name__)
        
        placements = []
        slides = slide_text.split("###")
        
        for slide_idx, slide in enumerate(slides):
            if not slide.strip():
                continue
            
            # Find all [IMAGE_n] markers
            image_markers = re.findall(r'\[IMAGE_(\d+)\]', slide)
            
            for marker in image_markers:
                img_idx = int(marker) - 1  # Convert to 0-based index
                if 0 <= img_idx < len(document_images):
                    img_data = document_images[img_idx]
                    placements.append({
                        'slide_index': slide_idx,
                        'image_id': img_data['id'],
                        'image_path': img_data['image_path'],
                        'marker': f'[IMAGE_{marker}]'
                    })
                    logger.info(f"Image placement: slide {slide_idx}, image {img_data['id']}")
        
        return placements
    
    def _generate_basic_slide_content(self, structured_content, slide_count, instructions, language, title):
        """Fallback method for generating slide content without AI"""
        content = structured_content['full_text']
        sections = structured_content['sections']
        key_topics = structured_content['key_topics']
        
        if slide_count == 'auto':
            slide_count = min(max(3, len(sections)), 10)
        
        slides_text = f"### {title or 'Document Analysis'}\n"
        slides_text += f"• Overview of key concepts\n"
        slides_text += f"• Based on {len(structured_content['sources'])} document(s)\n"
        slides_text += f"• Educational content analysis\n\n"
        
        # Generate content slides
        if sections:
            for i, section in enumerate(sections[:slide_count-1]):
                slides_text += f"### {section['title'][:50]}\n"
                bullet_points = self._generate_bullet_points(section['content'])
                for bullet in bullet_points[:4]:
                    slides_text += f"• {bullet}\n"
                slides_text += "\n"
        else:
            # Generate slides based on key topics
            topics_per_slide = max(1, len(key_topics) // (slide_count - 1))
            for i in range(0, min(len(key_topics), (slide_count - 1) * topics_per_slide), topics_per_slide):
                slide_topics = key_topics[i:i + topics_per_slide]
                slides_text += f"### Key Concepts: {', '.join(slide_topics[:2])}\n"
                for topic in slide_topics[:4]:
                    slides_text += f"• Understanding {topic.title()}\n"
                slides_text += "\n"
        
        return slides_text
    
    def _load_image_stream(self, path_or_url):
        """Load image from path or URL"""
        if not path_or_url:
            return None
        
        try:
            if str(path_or_url).startswith("http"):
                import requests
                resp = requests.get(path_or_url, timeout=15)
                resp.raise_for_status()
                return BytesIO(resp.content)
            elif os.path.exists(path_or_url):
                return open(path_or_url, "rb")
            else:
                return None
        except Exception as e:
            logger.warning(f"Could not load image {path_or_url}: {str(e)}")
            return None
    
    def _create_advanced_powerpoint(self, slide_content_text, template, title, user, background_image=None, image_placements=[], document_images=[]):
        """Create PowerPoint presentation with advanced styling, background, logo, and images"""
        try:
            import logging
            import re
            import os
            from io import BytesIO
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from django.conf import settings
            from django.utils import timezone
            
            logger = logging.getLogger(__name__)
            
            # Create presentation
            prs = Presentation()
            slide_width, slide_height = prs.slide_width, prs.slide_height
            slide_layout = prs.slide_layouts[6]  # blank layout for full control
            
            # Define template colors
            template_colors = self._get_template_colors(template)
            
            # Load background: prefer uploaded image, fallback to media defaults
            bg_stream = None
            if background_image:
                try:
                    # background_image is InMemoryUploadedFile
                    content = background_image.read()
                    bg_stream = BytesIO(content)
                except Exception as e:
                    logger.warning(f"Could not read uploaded background image: {e}")
            if not bg_stream:
                # Try multiple possible filenames for flexibility
                bg_image_paths = [
                    os.path.join(settings.MEDIA_ROOT, 'images', 'ppt_background.jpg'),
                    os.path.join(settings.MEDIA_ROOT, 'images', 'ppt.jpg'),
                    os.path.join(settings.MEDIA_ROOT, 'images', 'background.jpg')
                ]
                for bg_path in bg_image_paths:
                    bg_stream = self._load_image_stream(bg_path)
                    if bg_stream:
                        break
            
            # Split content into slides
            slides = slide_content_text.split("###")
            
            for i, slide in enumerate(slides):
                if not slide.strip():
                    continue
                    
                lines = slide.strip().split("\n")
                slide_title = self._sanitize_text(lines[0].strip())
                
                # Clean up slide title - remove "Slide" prefix and numbers
                slide_title = slide_title.replace("Slide", "").strip()
                # Remove leading numbers and dots/colons
                slide_title = re.sub(r'^\d+[.:]\s*', '', slide_title).strip()
                # Remove any remaining "Slide i" patterns
                slide_title = re.sub(r'^Slide\s+\d+\s*[-:.]?\s*', '', slide_title, flags=re.IGNORECASE).strip()
                
                # Separate bullet points and image markers
                body_lines = []
                slide_images = []
                
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for image marker
                    image_match = re.search(r'\[IMAGE_(\d+)\]', line)
                    if image_match:
                        img_idx = int(image_match.group(1)) - 1
                        if 0 <= img_idx < len(document_images):
                            slide_images.append(document_images[img_idx])
                        # Remove the marker from the line
                        line = re.sub(r'\[IMAGE_\d+\]', '', line).strip()
                    
                    if line.startswith('•'):
                        body_lines.append(self._sanitize_text(line))
                
                slide_obj = prs.slides.add_slide(slide_layout)
                
                # Add background image
                if bg_stream:
                    bg_stream.seek(0)
                    slide_obj.shapes.add_picture(bg_stream, 0, 0, width=slide_width, height=slide_height)
                else:
                    # Add colored background
                    background = slide_obj.background
                    fill = background.fill
                    fill.solid()
                    fill.fore_color.rgb = template_colors['background']
                
                # Add title
                title_box = slide_obj.shapes.add_textbox(
                    Inches(0), Inches(0.1),
                    slide_width, Inches(0.8)
                )
                title_tf = title_box.text_frame
                title_tf.word_wrap = True
                title_tf.margin_left = Inches(0.5)
                title_tf.margin_right = Inches(0.5)
                
                # Center the title
                max_chars_per_line = 80
                title_length = len(slide_title)
                if title_length < max_chars_per_line:
                    spaces_needed = (max_chars_per_line - title_length) // 2
                    centered_title = " " * spaces_needed + slide_title
                else:
                    centered_title = slide_title
                
                p = title_tf.add_paragraph()
                p.text = self._sanitize_text(centered_title)
                from pptx.enum.text import PP_ALIGN
                p.alignment = PP_ALIGN.LEFT
                run = p.runs[0]
                run.font.size = Pt(28)
                run.font.bold = True
                run.font.color.rgb = template_colors['title']
                
                # Determine layout based on whether images are present
                has_images = len(slide_images) > 0
                
                if has_images:
                    # Two-column layout: text on left, image on right
                    content_box = slide_obj.shapes.add_textbox(
                        Inches(0.8), Inches(1.4),
                        slide_width / 2 - Inches(1.2), slide_height - Inches(2.0)
                    )
                    
                    # Add image on the right side
                    if slide_images[0]['image_path'] and os.path.exists(slide_images[0]['image_path']):
                        try:
                            img_left = slide_width / 2 + Inches(0.2)
                            img_top = Inches(1.6)
                            img_width = slide_width / 2 - Inches(1.0)
                            img_height = slide_height - Inches(2.4)
                            
                            slide_obj.shapes.add_picture(
                                slide_images[0]['image_path'],
                                img_left, img_top,
                                width=img_width,
                                height=img_height
                            )
                            logger.info(f"Added image to slide {i}: {slide_images[0]['image_path']}")
                        except Exception as e:
                            logger.warning(f"Could not add image to slide: {e}")
                else:
                    # Full-width text layout
                    content_box = slide_obj.shapes.add_textbox(
                        Inches(0.8), Inches(1.4),
                        slide_width - Inches(1.6), slide_height - Inches(2.0)
                    )
                
                # Add bullet points
                if body_lines:
                    content_tf = content_box.text_frame
                    content_tf.word_wrap = True
                    content_tf.margin_left = Inches(0.2)
                    content_tf.margin_right = Inches(0.2)
                    content_tf.margin_top = Inches(0.1)
                    content_tf.margin_bottom = Inches(0.1)
                    
                    for line in body_lines:
                        p = content_tf.add_paragraph()
                        clean_line = self._sanitize_text(line.replace('•', '').strip())
                        
                        p.level = 0
                        p.space_after = Pt(8)
                        
                        # Handle colon definitions
                        if ':' in clean_line:
                            parts = clean_line.split(':', 1)
                            definition_term = parts[0].strip()
                            definition_explanation = parts[1].strip() if len(parts) > 1 else ""
                            
                            p.text = "• " + definition_term + ":"
                            run = p.runs[0]
                            run.font.size = Pt(24)
                            run.font.color.rgb = RGBColor(204, 0, 0)
                            run.font.bold = False
                            
                            if definition_explanation:
                                explanation_run = p.add_run()
                                explanation_run.text = " " + definition_explanation
                                explanation_run.font.size = Pt(24)
                                explanation_run.font.color.rgb = template_colors['content']
                                explanation_run.font.bold = False
                        else:
                            bullet_text = "• " + clean_line
                            p.text = bullet_text
                            run = p.runs[0]
                            run.font.size = Pt(24)
                            run.font.color.rgb = template_colors['content']
                            run.font.bold = False
            
            # Save presentation
            filename = f"{title or 'Generated_Presentation'}_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            filepath = os.path.join(settings.MEDIA_ROOT, 'generated_slides', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            prs.save(filepath)
            
            # Close streams
            if bg_stream:
                bg_stream.close()
            
            logger.info(f"PowerPoint created successfully with {len(image_placements)} images: {filename}")
            return filename
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating PowerPoint: {str(e)}")
            raise
    
    def _get_template_colors(self, template):
        """Get color scheme based on template"""
        try:
            from pptx.dml.color import RGBColor
        except ImportError:
            # Fallback if pptx is not available
            logger.warning("python-pptx not installed, using fallback colors")
            return {
                'background': (240, 248, 255),  # Light blue as tuple
                'title': (0, 102, 204),         # Blue as tuple
                'content': (51, 51, 51)         # Dark gray as tuple
            }
        
        color_schemes = {
            'professional': {
                'background': RGBColor(240, 248, 255),  # Light blue
                'title': RGBColor(0, 102, 204),         # Blue
                'content': RGBColor(51, 51, 51)         # Dark gray
            },
            'academic': {
                'background': RGBColor(248, 248, 255),  # Very light purple
                'title': RGBColor(75, 0, 130),          # Indigo
                'content': RGBColor(25, 25, 112)        # Navy blue
            },
            'creative': {
                'background': RGBColor(255, 248, 220),  # Light yellow
                'title': RGBColor(255, 140, 0),         # Orange
                'content': RGBColor(139, 69, 19)        # Brown
            },
            'minimal': {
                'background': RGBColor(255, 255, 255),  # White
                'title': RGBColor(64, 64, 64),          # Dark gray
                'content': RGBColor(96, 96, 96)         # Medium gray
            },
            'corporate': {
                'background': RGBColor(245, 245, 245),  # Light gray
                'title': RGBColor(0, 51, 102),          # Corporate blue
                'content': RGBColor(51, 51, 51)         # Dark gray
            }
        }
        
        return color_schemes.get(template, color_schemes['professional'])
    
    def _process_uploaded_files(self, files, documents=None):
        """Process and extract text from uploaded files"""
        all_content = []
        logger.info(f"Starting to process {len(files)} files")
        
        # Create a mapping from file names to documents if documents are provided
        file_to_document = {}
        if documents:
            for doc in documents:
                # Get the filename from the file path
                import os
                file_basename = os.path.basename(doc.file.name)
                file_to_document[file_basename] = doc
        
        for i, file in enumerate(files):
            try:
                logger.info(f"Processing file: {file.name}")
                
                # Check if we have a corresponding Document object with processed text
                file_basename = os.path.basename(file.name)
                corresponding_doc = file_to_document.get(file_basename)
                
                if corresponding_doc and hasattr(corresponding_doc, 'processed_text') and corresponding_doc.processed_text:
                    logger.info(f"Using processed text from Document model for {file.name} (processing mode: {getattr(corresponding_doc, 'processing_mode', 'unknown')})")
                    content = corresponding_doc.processed_text
                else:
                    # Fall back to direct file processing
                    logger.info(f"No processed text found, extracting directly from file: {file.name}")
                    
                    # Check file extension
                    file_extension = file.name.lower().split('.')[-1]
                    if f'.{file_extension}' not in self.supported_formats:
                        logger.warning(f"Unsupported file format: {file.name}")
                        continue
                    
                    # Extract text based on file type
                    if file_extension == 'pdf':
                        content = self._extract_pdf_content(file)
                    elif file_extension in ['doc', 'docx']:
                        content = self._extract_word_content(file)
                    elif file_extension == 'txt':
                        content = self._extract_text_content(file)
                    elif file_extension in ['ppt', 'pptx']:
                        content = self._extract_powerpoint_content(file)
                    else:
                        continue

                if content and content.strip():
                    all_content.append({
                        'filename': file.name,
                        'content': content.strip(),
                        'type': corresponding_doc.document_type if corresponding_doc else file.name.lower().split('.')[-1],
                        'processing_mode': getattr(corresponding_doc, 'processing_mode', 'unknown') if corresponding_doc else 'direct'
                    })
                    logger.info(f"Successfully processed file: {file.name}, content length: {len(content)}")
                else:
                    logger.warning(f"No content extracted from file: {file.name}")
                    
            except Exception as e:
                logger.warning(f"Error processing file {file.name}: {str(e)}")
                continue
        
        logger.info(f"Finished processing files. Total content items: {len(all_content)}")
        return all_content
    
    def _extract_pdf_content(self, file):
        """Extract text from PDF file"""
        try:
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF content: {str(e)}")
            return ""
    
    def _extract_word_content(self, file):
        """Extract text from Word document"""
        try:
            import docx
            import io
            
            doc = docx.Document(io.BytesIO(file.read()))
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting Word content: {str(e)}")
            return ""
    
    def _extract_text_content(self, file):
        """Extract text from plain text file"""
        try:
            return file.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            return ""
    
    def _extract_powerpoint_content(self, file):
        """Extract text from PowerPoint file"""
        try:
            from pptx import Presentation
            import io
            
            prs = Presentation(io.BytesIO(file.read()))
            text = ""
            
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PowerPoint content: {str(e)}")
            return ""
    
    def _extract_content_structure(self, processed_content, document_images=[]):
        """Analyze and structure the extracted content including image OCR text"""
        combined_text = ""
        sources = []
        
        for content_item in processed_content:
            combined_text += f"\n--- From {content_item['filename']} ---\n"
            combined_text += content_item['content']
            sources.append(content_item['filename'])
        
        # Add image OCR text to content
        if document_images:
            combined_text += "\n\n--- Image OCR Text ---\n"
            for img in document_images:
                if img['ocr_text']:
                    combined_text += f"\n[Image from page {img['page_number']}]: {img['ocr_text']}\n"
        
        # Basic content analysis
        sections = self._identify_sections(combined_text)
        key_topics = self._extract_key_topics(combined_text)
        
        return {
            'full_text': combined_text,
            'sources': sources,
            'sections': sections,
            'key_topics': key_topics,
            'word_count': len(combined_text.split()),
            'image_count': len(document_images)
        }
    
    def _identify_sections(self, text):
        """Identify main sections in the text"""
        # Simple section identification based on common patterns
        import re
        
        sections = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for headings (all caps, numbered, or specific patterns)
            if (re.match(r'^\d+\.', line) or 
                re.match(r'^[A-Z\s]{10,}$', line) or
                re.match(r'^(Chapter|Section|Part)', line, re.IGNORECASE)):
                sections.append({
                    'title': line,
                    'line_number': i,
                    'content': self._get_section_content(lines, i)
                })
        
        return sections[:10]  # Limit to first 10 sections
    
    def _get_section_content(self, lines, start_line):
        """Get content for a specific section"""
        content = []
        for i in range(start_line + 1, min(start_line + 20, len(lines))):
            if lines[i].strip():
                content.append(lines[i].strip())
            if len(content) > 10:  # Limit content length
                break
        return ' '.join(content)
    
    def _extract_key_topics(self, text):
        """Extract key topics from the text"""
        # Simple keyword extraction (in a real implementation, you'd use NLP)
        import re
        from collections import Counter
        
        # Remove common words and extract meaningful terms
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        common_words = {'that', 'this', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'more', 'very', 'when', 'come', 'may', 'into', 'over', 'think', 'also', 'your', 'work', 'life', 'only', 'can', 'still', 'should', 'after', 'being', 'now', 'made', 'before', 'here', 'through', 'when', 'where', 'much', 'take', 'than', 'only', 'think', 'know', 'just', 'first', 'could', 'right', 'would', 'about', 'there', 'what', 'some'}
        
        filtered_words = [word for word in words if word not in common_words and len(word) > 4]
        
        return [word for word, count in Counter(filtered_words).most_common(15)]
    
    def _generate_slide_content(self, structured_content, slide_count, instructions, language):
        """Generate content for slides using AI (simplified version)"""
        # This is a simplified version. In production, you'd use OpenAI or other AI services
        
        slides = []
        content = structured_content['full_text']
        sections = structured_content['sections']
        key_topics = structured_content['key_topics']
        
        # Determine actual slide count
        if slide_count == 'auto':
            slide_count = min(max(3, len(sections)), 15)
        
        # Generate title slide
        slides.append({
            'type': 'title',
            'title': self._generate_presentation_title(content, key_topics),
            'subtitle': f"Based on {len(structured_content['sources'])} document(s)",
            'content': []
        })
        
        # Generate content slides
        if sections:
            # Use identified sections
            for i, section in enumerate(sections[:slide_count-2]):
                slides.append({
                    'type': 'content',
                    'title': section['title'][:60],  # Limit title length
                    'content': self._generate_bullet_points(section['content'])
                })
        else:
            # Generate slides based on key topics
            topics_per_slide = max(1, len(key_topics) // (slide_count - 2))
            for i in range(0, min(len(key_topics), (slide_count - 2) * topics_per_slide), topics_per_slide):
                slide_topics = key_topics[i:i + topics_per_slide]
                slides.append({
                    'type': 'content',
                    'title': f"Key Concepts: {', '.join(slide_topics[:2])}",
                    'content': self._generate_bullet_points_from_topics(content, slide_topics)
                })
        
        # Generate conclusion slide
        if len(slides) < slide_count:
            slides.append({
                'type': 'conclusion',
                'title': 'Summary',
                'content': self._generate_summary_points(key_topics[:5])
            })
        
        return slides[:slide_count]
    
    def _generate_presentation_title(self, content, key_topics):
        """Generate a title for the presentation"""
        if key_topics:
            return f"{key_topics[0].title()} and Related Concepts"
        else:
            return "Document Analysis Presentation"
    
    def _generate_bullet_points(self, content):
        """Generate bullet points from content"""
        sentences = content.split('.')
        bullets = []
        
        for sentence in sentences[:5]:  # Max 5 bullet points
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                bullets.append(sentence.capitalize())
        
        return bullets or ["Key information from the document"]
    
    def _generate_bullet_points_from_topics(self, content, topics):
        """Generate bullet points based on topics"""
        bullets = []
        for topic in topics[:4]:  # Max 4 bullets
            bullets.append(f"Understanding {topic.title()}")
            bullets.append(f"Applications of {topic.title()}")
        
        return bullets[:5]  # Limit to 5 bullets
    
    def _generate_summary_points(self, key_topics):
        """Generate summary points"""
        return [f"Covered {topic.title()}" for topic in key_topics[:4]]
    
    def _create_powerpoint_presentation(self, slide_content, template, title, user):
        """Create the actual PowerPoint presentation"""
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            import os
            from django.conf import settings
            from django.utils import timezone
            
            # Create presentation
            prs = Presentation()
            
            # Apply template styling
            self._apply_template_styling(prs, template)
            
            # Create slides
            for slide_data in slide_content:
                if slide_data['type'] == 'title':
                    self._create_title_slide(prs, slide_data, template)
                elif slide_data['type'] in ['content', 'conclusion']:
                    self._create_content_slide(prs, slide_data, template)
            
            # Save presentation
            filename = f"{title or 'Generated_Presentation'}_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            filepath = os.path.join(settings.MEDIA_ROOT, 'generated_slides', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            prs.save(filepath)
            
            return filename
            
        except Exception as e:
            logger.error(f"Error creating PowerPoint: {str(e)}")
            raise
    
    def _apply_template_styling(self, prs, template):
        """Apply template-specific styling to the presentation"""
        # Template styling would be implemented here
        # For now, we'll use default styling
        pass
    
    def _create_title_slide(self, prs, slide_data, template):
        """Create a title slide"""
        slide_layout = prs.slide_layouts[0]  # Title slide layout
        slide = prs.slides.add_slide(slide_layout)
        
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        
        title.text = slide_data['title']
        subtitle.text = slide_data['subtitle']
    
    def _create_content_slide(self, prs, slide_data, template):
        """Create a content slide with bullet points"""
        slide_layout = prs.slide_layouts[1]  # Content slide layout
        slide = prs.slides.add_slide(slide_layout)
        
        title = slide.shapes.title
        content = slide.placeholders[1]
        
        title.text = slide_data['title']
        
        tf = content.text_frame
        tf.clear()
        
        for bullet_point in slide_data['content']:
            p = tf.add_paragraph()
            p.text = bullet_point
            p.level = 0
