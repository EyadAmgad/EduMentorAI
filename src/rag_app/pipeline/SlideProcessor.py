import logging
import re
import os
from io import BytesIO
import tempfile
import requests
from PIL import Image

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
            logger.info("=" * 70)
            logger.info("🚀 STARTING SLIDE GENERATION PROCESS")
            logger.info("=" * 70)
            logger.info(f"📋 Parameters:")
            logger.info(f"   - Files: {len(files)}")
            logger.info(f"   - Requested slides: {slide_count}")
            logger.info(f"   - Template: {template}")
            logger.info(f"   - Language: {language}")
            logger.info(f"   - Title: {title}")
            logger.info("=" * 70)
            
            # Step 1: Validate and process uploaded files
            logger.info("📂 STEP 1: Processing uploaded files...")
            logger.info("=" * 70)
            processed_content = self._process_uploaded_files(files, documents)
            if not processed_content:
                return {'success': False, 'error': 'No valid content found in uploaded files'}
            logger.info(f"✅ Successfully processed {len(processed_content)} file(s)")
            
            # Step 2: Extract images from documents if available
            logger.info("=" * 60)
            logger.info("🖼️  STEP 2: Extracting images from documents...")
            logger.info("=" * 60)
            document_images = []
            if documents:
                document_images = self._extract_document_images(documents)
                logger.info(f"✅ Found {len(document_images)} images across {len(documents)} documents")
            else:
                logger.info("⏭️  No document images to extract")
            
            # Step 3: Extract and structure content
            logger.info("=" * 60)
            logger.info("📊 STEP 3: Structuring content for presentation...")
            logger.info("=" * 60)
            structured_content = self._extract_content_structure(processed_content, document_images)
            logger.info(f"✅ Content structured successfully")
            logger.info(f"   - Sections: {len(structured_content.get('sections', []))}")
            logger.info(f"   - Total text length: {len(structured_content.get('full_text', ''))} characters")
            
            # Step 4: Generate slide content FIRST (without internet images)
            logger.info("=" * 60)
            logger.info("📝 STEP 4: Generating slide content using LLM...")
            logger.info("=" * 60)
            if self.llm_available and self.rag_model:
                slide_content_text = self._generate_ai_slide_content_without_images(
                    structured_content, slide_count, instructions, language, title
                )
            else:
                # Fallback to basic generation
                slide_content_text = self._generate_basic_slide_content(
                    structured_content, slide_count, instructions, language, title
                )
            
            # Log the generated content preview
            logger.info("✅ Slide content generated successfully")
            logger.info(f"Generated content preview (first 500 chars):\n{slide_content_text[:500]}...")
            
            # Step 5: Extract slide titles
            logger.info("=" * 60)
            logger.info("🔍 STEP 5: Extracting slide titles from generated content...")
            logger.info("=" * 60)
            slide_titles = self._extract_slide_titles(slide_content_text)
            logger.info(f"✅ Found {len(slide_titles)} slide titles:")
            for idx, title_text in enumerate(slide_titles):
                logger.info(f"   {idx + 1}. {title_text}")
            
            # Step 6: Calculate middle 3 slides dynamically based on total slides
            logger.info("=" * 60)
            logger.info("🎯 STEP 6: Calculating which slides should have images...")
            logger.info("=" * 60)
            internet_images = []
            total_slides = len(slide_titles)
            
            if total_slides >= 5:
                # Calculate the middle index
                middle_idx = total_slides // 2
                # Get 3 consecutive middle slides
                target_slide_indices = [middle_idx - 1, middle_idx, middle_idx + 1]
                logger.info(f"📊 Total slides: {total_slides}")
                logger.info(f"📍 Selected middle slides for images: {[i+1 for i in target_slide_indices]}")
            elif total_slides == 4:
                # For 4 slides: use slides 2, 3 (skip first and last)
                target_slide_indices = [1, 2]
                logger.info(f"📊 Total slides: {total_slides}")
                logger.info(f"📍 Selected slides for images: {[i+1 for i in target_slide_indices]}")
            elif total_slides == 3:
                # For 3 slides: use only slide 2
                target_slide_indices = [1]
                logger.info(f"📊 Total slides: {total_slides}")
                logger.info(f"📍 Selected slide for image: {[i+1 for i in target_slide_indices]}")
            else:
                # Too few slides for images
                target_slide_indices = []
                logger.info(f"📊 Total slides: {total_slides}")
                logger.info(f"⚠️  Not enough slides for images (minimum 3 required)")
            
            if target_slide_indices:
                try:
                    logger.info("=" * 60)
                    logger.info("🌐 STEP 7: Searching for images on the internet...")
                    logger.info("=" * 60)
                    
                    # Search for ONE image per slide based on slide title
                    for slide_idx in target_slide_indices:
                        if slide_idx < len(slide_titles):
                            slide_title = slide_titles[slide_idx]
                            logger.info(f"\n🔍 Slide {slide_idx + 1}: Searching for '{slide_title}'...")
                            
                            # IMPORTANT: PowerPoint split creates empty first element, so actual slide is at index+1
                            # Title index 0 → PowerPoint slide index 1, etc.
                            ppt_slide_index = slide_idx + 1
                            
                            # Search for exactly 1 image using the slide title
                            images = self._search_and_download_images(slide_title, num_images=1, slide_index=ppt_slide_index)
                            if images:
                                internet_images.append(images[0])
                                logger.info(f"   ✅ Found and downloaded image for slide {slide_idx + 1}")
                            else:
                                logger.info(f"   ⚠️  No image found for slide {slide_idx + 1}")
                    
                    logger.info("=" * 60)
                    logger.info(f"✅ Successfully downloaded {len(internet_images)} images from internet")
                    logger.info("=" * 60)
                except Exception as e:
                    logger.error(f"❌ Internet image search failed: {str(e)}", exc_info=True)
            else:
                logger.info(f"⏭️  Skipping image search - presentation has only {len(slide_titles)} slides")
            
            # Step 8: Match images to appropriate slides
            logger.info("=" * 60)
            logger.info("🔗 STEP 8: Matching images to slides...")
            logger.info("=" * 60)
            all_images = document_images + internet_images
            image_placements = self._match_images_to_slides(slide_content_text, all_images)
            logger.info(f"✅ Matched {len(image_placements)} images to slides")
            
            # Step 9: Create PowerPoint presentation with advanced styling and images
            logger.info("=" * 60)
            logger.info("🎨 STEP 9: Creating PowerPoint presentation...")
            logger.info("=" * 60)
            presentation_path = self._create_advanced_powerpoint(
                slide_content_text, template, title, user, background_image, image_placements, all_images
            )
            
            logger.info("=" * 70)
            logger.info("🎉 PRESENTATION GENERATED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info(f"📁 File path: {presentation_path}")
            logger.info(f"📊 Summary:")
            logger.info(f"   - Total slides: {len(slide_titles)}")
            logger.info(f"   - Images added: {len(image_placements)}")
            logger.info(f"   - Template: {template}")
            logger.info("=" * 70)
            
            # Step 10: Return success response with download URL
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

    def _extract_image_search_query_from_slide(self, slide_content):
        """
        Use LLM to extract a specific image search query from slide content.
        
        Args:
            slide_content: Full slide content including title and bullet points
            
        Returns:
            A concise search query string
        """
        try:
            if not self.llm_available or not self.rag_model:
                # Fallback: extract title
                lines = slide_content.strip().split("\n")
                if lines:
                    title = lines[0].strip()
                    title = re.sub(r'[^\w\s-]', '', title).strip()
                    return title if title else "image"
                return "image"
            
            # Use LLM to generate a specific search query
            prompt = f"""Based on this slide content, generate a SHORT and SPECIFIC image search query (2-4 words) that would find the most relevant image.

Slide Content:
{slide_content[:500]}

Instructions:
- Extract the main topic or concept from the slide
- Make it specific and visual (something you can see in an image)
- Keep it SHORT (2-4 words maximum)
- Do NOT include words like "image", "picture", "diagram"
- Return ONLY the search query, nothing else

Example:
If slide is about "Neural Networks Architecture", return: "neural network diagram"
If slide is about "Python Data Types", return: "python data types"

Your search query:"""
            
            messages = [
                {"role": "system", "content": "You are an expert at creating concise image search queries. Return only the search query, nothing else."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.rag_model._generate_llm_response(messages)
            
            if response['success']:
                query = response['answer'].strip()
                # Clean up the query
                query = query.replace('"', '').replace("'", "").strip()
                query = re.sub(r'[^\w\s-]', '', query).strip()
                return query[:100] if query else "image"
            else:
                # Fallback to title
                lines = slide_content.strip().split("\n")
                if lines:
                    title = lines[0].strip()
                    title = re.sub(r'[^\w\s-]', '', title).strip()
                    return title if title else "image"
                return "image"
                
        except Exception as e:
            logger.warning(f"Error extracting search query from slide: {str(e)}")
            # Fallback to title extraction
            lines = slide_content.strip().split("\n")
            if lines:
                title = lines[0].strip()
                title = re.sub(r'[^\w\s-]', '', title).strip()
                return title if title else "image"
            return "image"

    def _sanitize_text(self, text):
        try:
            if not isinstance(text, str):
                text = str(text)
            text = re.sub(r"[\ud800-\udfff]", "", text)
            text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            return text
        except Exception:
            return ''
    
    def _remove_think_tags(self, text):
        """
        Remove <think>...</think> tags and their content from the text.
        
        Args:
            text: Input text that may contain <think> tags
            
        Returns:
            Text with <think> tags and their content removed
        """
        try:
            if not isinstance(text, str):
                text = str(text)
            # Remove <think>...</think> blocks (case-insensitive, multiline)
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
            # Also remove any orphaned opening or closing tags
            text = re.sub(r'</?think>', '', text, flags=re.IGNORECASE)
            # Clean up any extra whitespace left behind
            text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
            return text.strip()
        except Exception as e:
            logger.warning(f"Error removing think tags: {str(e)}")
            return text
    
    def _extract_slide_titles(self, slide_content_text):
        """
        Extract slide titles from generated slide content.
        
        Args:
            slide_content_text: The full slide content text with ### markers
            
        Returns:
            List of slide titles
        """
        try:
            titles = []
            slides = slide_content_text.split("###")
            
            for idx, slide in enumerate(slides):
                if not slide.strip():
                    continue
                    
                lines = slide.strip().split("\n")
                if lines:
                    title = lines[0].strip()
                    original_title = title  # Keep original for fallback
                    
                    # Clean up title - remove "Slide", "Title" prefixes
                    title = title.replace("Slide", "").strip()
                    title = title.replace("Title", "").strip()
                    title = title.replace("title", "").strip()
                    title = re.sub(r'^Slide\s+\d+\s*[-:.]?\s*', '', title, flags=re.IGNORECASE).strip()
                    title = re.sub(r'^Title\s*[-:.]?\s*', '', title, flags=re.IGNORECASE).strip()
                    
                    # Remove leading numbers ONLY if there's text after them
                    # "1. Introduction" -> "Introduction"  (good)
                    # "1." -> keep as "Slide 1"  (fallback for bad LLM output)
                    match = re.match(r'^(\d+)[.:]\s*(.+)', title)
                    if match:
                        # Has number AND text after it - use the text
                        title = match.group(2).strip()
                    elif re.match(r'^\d+[.:]\s*$', title):
                        # ONLY a number - use fallback
                        title = f"Slide {len(titles) + 1}"
                        logger.warning(f"⚠️  Slide {idx} has no descriptive title ('{original_title}'), using fallback: '{title}'")
                    
                    # Remove leading/trailing colons or dashes
                    title = title.strip(':- ')
                    
                    if title:
                        titles.append(title)
                    else:
                        # Completely empty after cleaning - use fallback
                        fallback_title = f"Slide {len(titles) + 1}"
                        titles.append(fallback_title)
                        logger.warning(f"⚠️  Slide {idx} became empty after cleaning (was: '{original_title}'), using: '{fallback_title}'")
            
            return titles
        except Exception as e:
            logger.warning(f"Error extracting slide titles: {str(e)}")
            return []
    
    def _generate_search_queries_from_slides(self, slide_titles, max_queries=3):
        """
        Generate search queries from slide titles, skipping the first 3 slides.
        Returns queries for exactly max_queries slides starting from slide 4.
        
        Args:
            slide_titles: List of all slide titles
            max_queries: Number of slides to search images for (default: 3)
            
        Returns:
            List of tuples: [(search_query, slide_index), ...]
            slide_index corresponds to position in the slides array
        """
        try:
            queries_with_index = []
            
            # Skip the first 3 slides (indices 0, 1, 2)
            # Start from slide 4 (index 3) and get the next 3 slides
            start_index = 3  # Start from the 4th slide
            end_index = min(len(slide_titles), start_index + max_queries)
            
            logger.info(f"Skipping first 3 slides, searching images for slides {start_index} to {end_index-1}")
            
            for i in range(start_index, end_index):
                title = slide_titles[i]
                
                # Clean up title for search
                query = re.sub(r'[^\w\s-]', '', title).strip()
                
                if query:
                    queries_with_index.append((query, i))
                    logger.info(f"  Will search for slide {i}: '{query}'")
            
            return queries_with_index
        except Exception as e:
            logger.warning(f"Error generating search queries: {str(e)}")
            return []
    
    def _match_images_to_slides(self, slide_content_text, all_images):
        """
        Match downloaded images to appropriate slides based on search query.
        Each image is matched to the slide it was searched for.
        
        Args:
            slide_content_text: The full slide content text
            all_images: List of all available images (document + internet)
            
        Returns:
            List of image placement dicts: [{'slide_index': slide_idx, 'image': img_dict}]
        """
        try:
            placements = []
            used_slide_indices = set()  # Track which slides already have images
            
            # Get only internet images (they have the slide index info)
            internet_images = [img for img in all_images if img.get('source') == 'internet']
            
            if not internet_images:
                logger.info("No internet images available for matching")
                return placements
            
            # Each internet image has metadata about which slide it belongs to
            for img in internet_images:
                slide_idx = img.get('slide_index', 1)
                
                # Ensure no duplicate images on the same slide
                if slide_idx in used_slide_indices:
                    logger.warning(f"⚠️ Slide {slide_idx} already has an image, skipping duplicate")
                    continue
                
                placements.append({
                    'slide_index': slide_idx,
                    'image': img
                })
                used_slide_indices.add(slide_idx)
                logger.info(f"✅ Matched image '{img.get('ocr_text')}' to slide {slide_idx + 1}")
            
            logger.info(f"📊 Total unique image placements: {len(placements)}")
            return placements
        except Exception as e:
            logger.error(f"Error matching images to slides: {str(e)}")
            return []
    
    def _generate_image_search_query(self, title, structured_content):
        """
        Generate a concise search query for finding relevant images based on presentation content.
        
        Args:
            title: Presentation title
            structured_content: Structured content dict with extracted information
            
        Returns:
            Search query string or None
        """
        try:
            # Use the title as the primary search query
            if title and len(title.strip()) > 0:
                # Clean up the title for search
                query = re.sub(r'[^\w\s-]', '', title).strip()
                return query
            
            # Fallback: use first heading or keywords from content
            if structured_content.get('headings'):
                first_heading = structured_content['headings'][0]
                query = re.sub(r'[^\w\s-]', '', first_heading).strip()
                return query
            
            return None
        except Exception as e:
            logger.warning(f"Error generating image search query: {str(e)}")
            return None
    
    def _search_and_download_images(self, query, num_images=3, slide_index=None):
        """
        Search for images using SerpApi and download them locally.
        
        Args:
            query: Search query string
            num_images: Maximum number of images to download (default: 3)
            slide_index: The slide index this image belongs to (optional)
            
        Returns:
            List of dicts with image info including slide_index
        """
        from django.conf import settings
        
        # Check if SerpApi key is configured
        serpapi_key = getattr(settings, 'SERPAPI_KEY', None)
        if not serpapi_key:
            logger.warning("⚠️ SERPAPI_KEY not configured. Skipping internet image search.")
            return []
        
        if slide_index is not None:
            logger.info(f"🔍 Starting image search for Slide {slide_index}: '{query}'")
        else:
            logger.info(f"🔍 Starting image search for query: '{query}'")
        
        try:
            from serpapi import GoogleSearch
        except ImportError:
            logger.error("❌ google-search-results package not installed. Run: pip install google-search-results")
            return []
        
        # Create temporary directory for downloaded images
        temp_dir = tempfile.mkdtemp(prefix='slide_images_')
        logger.info(f"📁 Created temp directory: {temp_dir}")
        image_data = []
        downloaded_urls = set()  # Track downloaded URLs to avoid duplicates
        
        try:
            params = {
                "engine": "google_images",
                "q": query,
                "api_key": serpapi_key,
                "num": num_images,
            }
            
            logger.info(f"🌐 Calling SerpApi with query: '{query}'")
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if 'error' in results:
                logger.error(f"❌ SerpApi error: {results['error']}")
                return []
            
            images_results = results.get("images_results", [])
            logger.info(f"📊 SerpApi returned {len(images_results)} image results")
            
            for i, res in enumerate(images_results[:num_images]):
                img_url = res.get("original") or res.get("thumbnail")
                if not img_url:
                    logger.warning(f"⚠️ No URL found for image {i+1}")
                    continue
                
                # Skip if we already downloaded this URL
                if img_url in downloaded_urls:
                    logger.warning(f"⚠️ Skipping duplicate image URL: {img_url[:100]}")
                    continue
                    
                try:
                    logger.info(f"⬇️ Downloading image {i+1}/{num_images} from: {img_url[:100]}...")
                    # Download image with timeout and proper headers to avoid 403 errors
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.google.com/'
                    }
                    response = requests.get(img_url, timeout=10, headers=headers)
                    response.raise_for_status()
                    
                    # Open and validate image
                    img = Image.open(BytesIO(response.content))
                    logger.info(f"✓ Image {i+1} downloaded: {img.size[0]}x{img.size[1]} pixels, mode: {img.mode}")
                    
                    # Save image
                    safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
                    filename = f"{safe_query}_{i+1}.jpg"
                    img_path = os.path.join(temp_dir, filename)
                    
                    # Convert to RGB if necessary (for PNG with transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img
                    
                    img.save(img_path, 'JPEG', quality=85)
                    
                    # Mark this URL as downloaded
                    downloaded_urls.add(img_url)
                    
                    image_data.append({
                        'id': f"internet_{len(image_data)}",  # Unique ID for internet images
                        'document_title': 'Internet Search',
                        'document_id': None,
                        'page_number': None,
                        'image_index': len(image_data),
                        'ocr_text': query,  # Use search query as description
                        'image_path': img_path,
                        'width': img.width,
                        'height': img.height,
                        'source': 'internet',  # Mark as internet source
                        'url': img_url,
                        'slide_index': slide_index  # Store which slide this image belongs to
                    })
                    
                    if slide_index is not None:
                        logger.info(f"✅ Successfully saved image for Slide {slide_index}: {img_path}")
                    else:
                        logger.info(f"✅ Successfully saved image {i+1}/{num_images}: {img_path}")
                    
                except Exception as e:
                    logger.warning(f"❌ Failed to download image from {img_url[:100]}: {str(e)}")
                    continue
            
            if slide_index is not None:
                logger.info(f"🎉 Downloaded {len(image_data)} image(s) for Slide {slide_index}: '{query}'")
            else:
                logger.info(f"🎉 Successfully downloaded {len(image_data)} images for query: '{query}'")
            return image_data
            
        except Exception as e:
            logger.error(f"❌ Error in image search: {str(e)}", exc_info=True)
            return []
    
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
    
    def _generate_ai_slide_content_without_images(self, structured_content, slide_count, instructions, language, title):
        """Generate slide content using the existing RAG model LLM WITHOUT image markers"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Prepare the content for AI processing
            content_summary = structured_content['full_text'][:8000]  # Limit content length
            
            # Determine slide count
            if slide_count == 'auto':
                slide_count = min(max(3, len(structured_content['sections'])), 10)
            else:
                # Convert to int if it's a string
                try:
                    slide_count = int(slide_count)
                except (ValueError, TypeError):
                    slide_count = 5  # Default fallback
            
            # Create the prompt for the LLM (NO image instructions)
            prompt = f"""
You MUST create EXACTLY {slide_count} slides. This is a strict requirement - no more, no less.

Document Content:
{content_summary}

STRICT REQUIREMENTS:
1. Create EXACTLY {slide_count} slides - count them before responding
2. Language: {language}
3. Presentation Title: {title or 'Document Analysis'}
4. Additional Instructions: {instructions}

Slide Structure:
- First slide: Title slide with "{title or 'Document Analysis'}"
- Slides 2 to {slide_count-1}: Content slides with 4-5 bullet points each
- Last slide: Summary or conclusion

Format EXACTLY like this (use DESCRIPTIVE titles, NOT numbers):
### Introduction to the Topic
• First bullet point
• Second bullet point
• Third bullet point

### Key Concepts Explained
• First bullet point
• Second bullet point

CRITICAL RULES:
1. You MUST create {slide_count} slides total
2. Each slide title must be DESCRIPTIVE (e.g., "Neural Networks Explained", "Applications of AI")
3. DO NOT use just numbers as titles (BAD: "1.", "2." - GOOD: "Introduction", "Main Concepts")
4. DO NOT include the word "Slide" or "Title" in slide titles
5. Use bullet points (•) for content
6. Keep content educational and well-structured

EXAMPLE OF GOOD SLIDE TITLES:
### Understanding Machine Learning
### Types of Neural Networks  
### Real-World Applications
### Future Trends and Challenges

EXAMPLE OF BAD SLIDE TITLES (DON'T DO THIS):
### 1.
### 2.
### Slide 1
### Title

COUNT YOUR SLIDES BEFORE RESPONDING - THERE MUST BE EXACTLY {slide_count} SLIDES WITH DESCRIPTIVE TITLES!

Now create the {slide_count} slides:
"""
            
            # Use the existing RAG model's LLM method
            system_message = "You are an expert educational content creator that creates well-structured, engaging presentation slides. Follow instructions precisely."
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Call the existing LLM method
            logger.info(f"📤 Sending request to LLM to generate {slide_count} slides...")
            response = self.rag_model._generate_llm_response(messages)
            
            if response['success']:
                slide_text = response['answer']
                logger.info(f"📥 Received LLM response ({len(slide_text)} characters)")
                
                # Count how many slides the LLM actually generated
                generated_count = slide_text.count('###')
                logger.info(f"📊 LLM generated {generated_count} slides (requested: {slide_count})")
                
                if generated_count != slide_count:
                    logger.warning(f"⚠️  WARNING: LLM generated {generated_count} slides but {slide_count} were requested!")
                
                # Remove <think> tags and their content
                slide_text = self._remove_think_tags(slide_text)
                
                # Log a preview of what was generated
                preview_lines = slide_text.split('\n')[:20]
                logger.info(f"📄 Generated content preview:\n" + '\n'.join(preview_lines))
                
                return slide_text
            else:
                logger.error(f"LLM generation failed: {response.get('error', 'Unknown error')}")
                # Fallback to basic generation
                return self._generate_basic_slide_content(structured_content, slide_count, instructions, language, title)
            
        except Exception as e:
            logger.error(f"Error in RAG slide generation: {str(e)}")
            # Fallback to basic generation
            return self._generate_basic_slide_content(structured_content, slide_count, instructions, language, title)
    
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
                image_context = "\n\n🖼️ AVAILABLE IMAGES:\n"
                for idx, img in enumerate(document_images, 1):
                    source = img.get('source', 'document')
                    if source == 'internet':
                        image_context += f"  [{idx}] Internet image about: {img['ocr_text']}\n"
                    else:
                        ocr_preview = img['ocr_text'][:200] if img['ocr_text'] else "No OCR text"
                        image_context += f"  [{idx}] Document image from page {img['page_number']}: {ocr_preview}\n"
                
                image_context += f"\n⚠️ IMPORTANT: You have {len(document_images)} images available. "
                image_context += "You MUST use these images by placing [IMAGE_n] markers in relevant slides. "
                image_context += "Distribute them across different slides (don't put all in one slide). "
                image_context += "Images will be displayed on the right side of slides without covering text.\n"
            
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
- **CRITICAL**: If images are available above, you MUST include [IMAGE_n] markers in relevant slides where n is the image number
- Distribute images across different slides - maximum 1 image per slide
- Place [IMAGE_n] marker as a separate bullet point or within a bullet point

Format each slide exactly like this:
### Slide Title Here
• First bullet point
• Second bullet point [IMAGE_1]
• Third bullet point
• Fourth bullet point

OR

### Slide Title Here
• First bullet point
• Second bullet point
• [IMAGE_2]
• Third bullet point

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
                # Remove <think> tags and their content
                slide_text = self._remove_think_tags(slide_text)
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
            logger.info(f"📊 PowerPoint creation: Split content into {len(slides)} sections")
            logger.info(f"📊 After filtering empty sections, will create slides...")
            
            slide_number = 0
            for i, slide in enumerate(slides):
                if not slide.strip():
                    logger.info(f"   Section {i}: EMPTY - skipping")
                    continue
                
                slide_number += 1
                logger.info(f"   Section {i}: Creating PowerPoint slide #{slide_number}")
                    
                lines = slide.strip().split("\n")
                slide_title = self._sanitize_text(lines[0].strip())
                
                # Clean up slide title - remove "Slide", "Title", prefixes and numbers
                slide_title = slide_title.replace("Slide", "").strip()
                slide_title = slide_title.replace("Title", "").strip()
                slide_title = slide_title.replace("title", "").strip()
                # Remove leading numbers and dots/colons
                slide_title = re.sub(r'^\d+[.:]\s*', '', slide_title).strip()
                # Remove any remaining "Slide i" or "Title:" patterns
                slide_title = re.sub(r'^Slide\s+\d+\s*[-:.]?\s*', '', slide_title, flags=re.IGNORECASE).strip()
                slide_title = re.sub(r'^Title\s*[-:.]?\s*', '', slide_title, flags=re.IGNORECASE).strip()
                # Remove leading/trailing colons or dashes
                slide_title = slide_title.strip(':- ')
                
                # Separate bullet points and image markers
                body_lines = []
                slide_images = []
                
                # Check if this slide has a matched image from image_placements
                logger.info(f"🔍 Checking slide {i} for images...")
                for placement in image_placements:
                    logger.info(f"   Placement: slide_index={placement['slide_index']}, current i={i}")
                    if placement['slide_index'] == i:
                        slide_images.append(placement['image'])
                        logger.info(f"   ✅ MATCHED! Adding image to slide {i}")
                
                if slide_images:
                    logger.info(f"📸 Slide {i} will have {len(slide_images)} image(s)")
                else:
                    logger.info(f"⚪ Slide {i} will have no images")
                
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Remove any old [IMAGE_n] markers if present
                    line = re.sub(r'\[IMAGE_\d+\]', '', line).strip()
                    
                    if line.startswith('•'):
                        body_lines.append(self._sanitize_text(line))
                
                # If this slide has images, limit bullet points to 3-4 for better layout
                if slide_images and len(body_lines) > 4:
                    body_lines = body_lines[:4]
                
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
                    logger.info(f"🖼️  Adding image to slide {i}...")
                    # Two-column layout: text on left, image on right
                    content_box = slide_obj.shapes.add_textbox(
                        Inches(0.8), Inches(1.4),
                        slide_width / 2 - Inches(1.2), slide_height - Inches(2.0)
                    )
                    
                    # Add image on the right side
                    image_path = slide_images[0].get('image_path')
                    logger.info(f"   Image path: {image_path}")
                    logger.info(f"   Path exists: {os.path.exists(image_path) if image_path else False}")
                    
                    if image_path and os.path.exists(image_path):
                        try:
                            img_left = slide_width / 2 + Inches(0.2)
                            img_top = Inches(1.6)
                            img_width = slide_width / 2 - Inches(1.0)
                            img_height = slide_height - Inches(2.4)
                            
                            slide_obj.shapes.add_picture(
                                image_path,
                                img_left, img_top,
                                width=img_width,
                                height=img_height
                            )
                            logger.info(f"   ✅ Successfully added image to slide {i}: {image_path}")
                        except Exception as e:
                            logger.error(f"   ❌ Could not add image to slide {i}: {e}")
                    else:
                        logger.warning(f"   ⚠️  Image path invalid or doesn't exist: {image_path}")
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
        import os  # Import at the top of the function
        
        all_content = []
        logger.info(f"Starting to process {len(files)} files")
        
        # Create a mapping from file names to documents if documents are provided
        file_to_document = {}
        if documents:
            for doc in documents:
                # Get the filename from the file path
                file_basename = os.path.basename(doc.file.name)
                file_to_document[file_basename] = doc
        
        for i, file in enumerate(files):
            try:
                logger.info(f"Processing file: {file.name}")
                
                # Check if we have a corresponding Document object with processed text
                file_basename = os.path.basename(file.name)
                corresponding_doc = file_to_document.get(file_basename)
                
                if corresponding_doc and hasattr(corresponding_doc, 'processed_text') and corresponding_doc.processed_text:
                    logger.info(f"✅ Using processed text from Document model for {file.name} (processing mode: {getattr(corresponding_doc, 'processing_mode', 'unknown')})")
                    content = corresponding_doc.processed_text
                    logger.info(f"   Content length: {len(content)} characters")
                else:
                    # Fall back to direct file processing
                    logger.info(f"📄 No processed text found, extracting directly from file: {file.name}")
                    
                    # Check file extension
                    file_extension = file.name.lower().split('.')[-1]
                    logger.info(f"   File extension: .{file_extension}")
                    logger.info(f"   Supported formats: {self.supported_formats}")
                    
                    if f'.{file_extension}' not in self.supported_formats:
                        logger.error(f"❌ Unsupported file format: {file.name} (.{file_extension})")
                        logger.error(f"   Supported formats are: {', '.join(self.supported_formats)}")
                        continue
                    
                    # Extract text based on file type
                    logger.info(f"   Extracting content from .{file_extension} file...")
                    try:
                        if file_extension == 'pdf':
                            content = self._extract_pdf_content(file)
                        elif file_extension in ['doc', 'docx']:
                            content = self._extract_word_content(file)
                        elif file_extension == 'txt':
                            content = self._extract_text_content(file)
                        elif file_extension in ['ppt', 'pptx']:
                            content = self._extract_powerpoint_content(file)
                        else:
                            logger.error(f"❌ No extraction method for .{file_extension}")
                            continue
                        
                        logger.info(f"   Extracted {len(content) if content else 0} characters")
                    except Exception as extract_error:
                        logger.error(f"❌ Error extracting content: {str(extract_error)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        content = None

                if content and content.strip():
                    all_content.append({
                        'filename': file.name,
                        'content': content.strip(),
                        'type': corresponding_doc.document_type if corresponding_doc else file.name.lower().split('.')[-1],
                        'processing_mode': getattr(corresponding_doc, 'processing_mode', 'unknown') if corresponding_doc else 'direct'
                    })
                    logger.info(f"✅ Successfully processed file: {file.name}, content length: {len(content)}")
                else:
                    logger.error(f"❌ No content extracted from file: {file.name}")
                    logger.error(f"   Content is: {repr(content)[:100] if content else 'None or empty'}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing file {file.name}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"=" * 60)
        logger.info(f"📊 File Processing Summary:")
        logger.info(f"   Files attempted: {len(files)}")
        logger.info(f"   Successfully processed: {len(all_content)}")
        logger.info(f"   Failed: {len(files) - len(all_content)}")
        logger.info(f"=" * 60)
        
        if len(all_content) == 0:
            logger.error("❌ CRITICAL: No valid content found in ANY uploaded files!")
            logger.error("   Possible reasons:")
            logger.error("   1. Files are empty or corrupted")
            logger.error("   2. File format not supported")
            logger.error("   3. Extraction libraries missing (PyPDF2, python-docx, etc.)")
            logger.error("   4. Files don't have Document objects with processed_text")
        
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
