# EduMentorAI - Media Setup Instructions

## Directory Structure Setup

To enable the advanced slide generation with backgrounds and logos, create the following directory structure in your project:

```
src/
├── media/
│   ├── images/
│   │   ├── ppt_background.jpg    # Background image for slides
│   │   └── logo.png              # Logo image (transparent PNG recommended)
│   └── generated_slides/         # Directory for generated presentations
```

## Setup Commands

Run these commands in your WSL terminal from the `src` directory:

```bash
# Create the directory structure
mkdir -p media/images
mkdir -p media/generated_slides

# Set appropriate permissions
chmod 755 media
chmod 755 media/images
chmod 755 media/generated_slides
```

## Image Requirements

### Background Image (ppt_background.jpg)
- Recommended size: 1920x1080 pixels (16:9 aspect ratio)
- Format: JPG or PNG
- Should be professional and not too busy (so text remains readable)
- Consider using a subtle gradient or corporate background

### Logo Image (logo.png)
- Recommended format: PNG with transparent background
- Recommended size: 200x200 pixels or similar square aspect ratio
- Should be your institution or project logo
- Will be placed in the top-right corner of each slide

## Installation Commands

Install the required packages:

```bash
pip install PyPDF2==3.0.1 python-docx==0.8.11 python-pptx==0.6.21
```

## Environment Variables

The slide generator uses the existing RAG model LLM configuration. 
Make sure your `.env` file has:

```env
# OpenRouter API Key for RAG model (already configured for chat)
OPEN_ROUTER_API_KEY=your-openrouter-api-key-here
```

This is the same API key used by your existing chat functionality.

## Features Enabled

With this setup, the slide generator will:
✅ Use the existing RAG model LLM for intelligent slide content creation
✅ Leverage the same AI infrastructure as your chat system
✅ Apply professional styling with custom backgrounds
✅ Add your logo to each slide
✅ Support multiple templates (Professional, Academic, Creative, Minimal, Corporate)
✅ Generate slides in multiple languages
✅ Create well-formatted bullet points and titles
✅ Automatically determine optimal slide count or use custom count

## Integration Benefits

By using the existing RAG model:
- ✅ **Consistent LLM usage** across the entire application
- ✅ **Shared configuration** - no need for separate API keys
- ✅ **Better error handling** - uses the same robust error handling as chat
- ✅ **Cost efficiency** - single LLM API integration
- ✅ **Maintenance simplicity** - one LLM system to maintain

## Fallback Mode

If the RAG model cannot be initialized (missing API key, etc.), the system will:
- Fall back to basic slide generation without AI
- Still apply custom styling and backgrounds
- Use keyword extraction for content structuring