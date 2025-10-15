# EduMentorAI

## Team
* [Eyad Amgad Mostafa](https://github.com/EyadAmgad)
* [Zyad Tarik Omar](https://github.com/ziadtarek12/)
* [Yousif Ibrahim Masoud](https://github.com/yousifmasoud)
* [Ahmed Mahmoud Abdelazim](https://github.com/ahmedomahmoud)
* [Hesham Ahmed Ebaid](https://github.com/heshamebaid)


An intelligent educational platform that revolutionizes learning through AI-powered document interaction, personalized chatbots, and automated quiz generation.

[![Live Demo](https://img.shields.io/badge/Live-Demo-blue?style=for-the-badge)](https://edumentorai-edumentorai.hf.space/)
[![Python](https://img.shields.io/badge/Python-3.12-green?style=for-the-badge&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-Latest-darkgreen?style=for-the-badge&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

## 🚀 Live Demo

**🌐 Live Application:** [Live Demo](https://edumentorai-edumentorai.hf.space/)

*Experience EduMentorAI's powerful features including document-based chat, intelligent quiz generation, and personalized learning assistance.*

## 📖 Overview

**EduMentorAI** is a cutting-edge educational platform that leverages **Retrieval-Augmented Generation (RAG)**, **LangChain**, and **Django** to create an intelligent learning ecosystem. The platform transforms static educational documents into interactive learning experiences through AI-powered conversations and automated assessment generation.

### 🎯 Key Capabilities

- **📚 Document Intelligence**: Upload and interact with PDFs, Word documents, PowerPoint presentations, and text files
- **💬 Smart Chat System**: Context-aware conversations with your documents using advanced RAG technology
- **📝 Automated Quiz Generation**: AI-powered creation of multiple-choice, true/false, and short-answer questions
- **🎓 Subject Management**: Organize content by courses and subjects for structured learning
- **👥 Multi-User Support**: User authentication, profiles, and personalized learning experiences
- **🔄 Real-time Processing**: Live document chunking and embedding generation for immediate interaction
- **📊 Google Forms Integration**: Seamless quiz export to Google Forms for broader distribution

## ✨ Features

### 🔍 Intelligent Document Processing
- **Multi-format Support**: PDF, DOCX, PPTX, and TXT file processing
- **Smart Chunking**: Automatic document segmentation for optimal RAG performance
- **Vector Embeddings**: Advanced semantic search using sentence transformers
- **Real-time Processing**: Immediate document analysis and indexing

### 💭 Advanced Chat System
- **Context-Aware Responses**: AI maintains conversation context across sessions
- **Document-Specific Chat**: Focused discussions on individual documents
- **Subject-Based Chat**: Comprehensive conversations across multiple course materials
- **Anonymous Chat**: Temporary document interaction without account requirements

### 📋 Automated Assessment Generation
- **Multiple Question Types**: MCQ, True/False, Short Answer, Fill-in-the-blank
- **Difficulty Adaptation**: AI-generated questions based on document complexity
- **Google Forms Export**: One-click quiz publishing to Google Forms
- **Performance Analytics**: Track quiz creation and completion metrics

### 👤 User Management
- **Secure Authentication**: Email verification and secure login system
- **User Profiles**: Customizable profiles with university and major information
- **Subject Organization**: Personal subject/course management system
- **Chat History**: Persistent conversation history across sessions

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.x with Django REST Framework
- **AI/ML**: LangChain, Sentence Transformers, FAISS
- **Database**: PostgreSQL (Aiven) with SQLite for development
- **File Processing**: PyMuPDF, PyPDF2, python-docx, python-pptx
- **Authentication**: Django Allauth with email verification

### Frontend
- **Templates**: Django Templates with responsive CSS
- **Styling**: Custom CSS with modern UI components
- **JavaScript**: Vanilla JS for dynamic interactions
- **File Upload**: Ajax-based file upload with progress tracking

### Infrastructure
- **Storage**: Local file storage with cloud storage options
- **Deployment**: Docker containerization
- **API Integration**: Google API for Forms integration

## 🚀 Installation & Setup

### Prerequisites

- **Python**: 3.9 or higher (recommended: 3.12)
- **Git**: Latest version
- **PostgreSQL**: 13+ (or use provided Aiven configuration)

### 1. Clone the Repository

```bash
git clone https://github.com/EyadAmgad/EduMentorAI.git
cd EduMentorAI
```

### 2. Environment Setup

#### Option A: Using Conda (Recommended)
```bash
# Create and activate conda environment
conda create -n edu-mentor python=3.12 -y
conda activate edu-mentor
```

#### Option B: Using Virtual Environment
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Navigate to source directory
cd src

# Install Python packages
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your configuration
nano .env  # or use your preferred editor
```

#### Required Environment Variables

```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database Configuration
# Set USE_SQLITE=True for local development with SQLite
# Set USE_SQLITE=False for production with PostgreSQL
USE_SQLITE=False

# Aiven PostgreSQL Configuration (when USE_SQLITE=False)
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
DB_HOST=your-aiven-host.aivencloud.com
DB_PORT=12345

# Email Configuration (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AI API Configuration
OPEN_ROUTER_API_KEY=your-openrouter-api-key
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-3.5-turbo
```

### 5. Database Setup

```bash
# Run database migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser

```

### 6. Static Files Setup

```bash
# Collect static files
python manage.py collectstatic --noinput
```

### 7. Development Server

```bash
# Start the development server
python manage.py runserver



The application will be available at `http://localhost:8000`

## 🐳 Docker Deployment

### Quick Start with Docker

```bash
# Build the Docker image
docker build -t edumetorai .

# Run the container
docker run -p 8000:7860 \
  -e SECRET_KEY=your-secret-key \
  -e DB_HOST=your-aiven-host.aivencloud.com \
  -e DB_NAME=your-database-name \
  -e DB_USER=your-database-user \
  -e DB_PASSWORD=your-database-password \
  edumetorai
```

### Docker Compose (Recommended for Development)

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:7860"
    environment:
      - DEBUG=True
      - SECRET_KEY=dev-secret-key
      - USE_SQLITE=True
    volumes:
      - ./src:/app/src
```

```bash
# Start with Docker Compose
docker-compose up --build
```

## 🔧 Configuration

### Aiven PostgreSQL Setup

1. **Create Aiven PostgreSQL Service**
   - Go to [aiven.io](https://aiven.io)
   - Create a new PostgreSQL service
   - Note your connection details (host, port, database name, user, password)

2. **Database Configuration**
   - The app uses PostgreSQL through Aiven
   - Run migrations to set up tables
   - Ensure SSL connection is enabled (default in Aiven)

3. **Connection Security**
   - Aiven provides SSL-enabled connections by default
   - Use the provided connection parameters in your environment variables
   - Ensure your IP is whitelisted if IP filtering is enabled

### AI Model Configuration

1. **Embedding Model**
   - Default: `sentence-transformers/all-MiniLM-L6-v2`
   - Downloads automatically on first use
   - Requires ~80MB storage space

2. **LLM Configuration**
   - Supports OpenRouter API
   - Configure your preferred model in environment variables
   - Ensure sufficient API credits for document processing

### Email Configuration

1. **Gmail SMTP Setup**
   - Enable 2-factor authentication
   - Generate an App Password
   - Use Gmail address and app password in environment variables

## 📚 Usage Guide

### For Students

1. **Account Creation**
   - Register with email verification
   - Complete your profile with university/major information

2. **Document Upload**
   - Create subjects for your courses
   - Upload course materials (PDF, DOCX, PPTX, TXT)
   - Wait for processing (usually < 30 seconds)

3. **Interactive Learning**
   - Start chat sessions with your documents
   - Ask questions about specific topics
   - Get contextual explanations and summaries

4. **Quiz Generation**
   - Generate practice quizzes from your documents
   - Export to Google Forms for sharing
   - Use various question types for comprehensive assessment

### For Educators

1. **Content Management**
   - Upload course materials and organize by subjects
   - Create comprehensive document libraries
   - Generate assessments automatically

2. **Quiz Creation**
   - Create quizzes from lecture notes or textbooks
   - Export to Google Forms for student distribution
   - Customize question types and difficulty levels

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Set up testing environment: `python manage.py setup_testing`
4. Create test data: `python manage.py create_test_data`
5. Make your changes
6. Add tests for new functionality: `python manage.py runtests --type unit`
7. Run all tests: `python manage.py runtests --coverage`
8. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for new functions and classes
- Write unit tests for new features

## 🧪 Testing

EduMentorAI includes a comprehensive testing infrastructure using Django's native management commands.

### Available Test Commands

```bash
# Run all tests
python manage.py runtests

# Run specific test types
python manage.py runtests --type unit
python manage.py runtests --type integration
python manage.py runtests --type models
python manage.py runtests --type views
python manage.py runtests --type forms

# Run with coverage report
python manage.py runtests --coverage

# Fast testing (skip slow tests)
python manage.py runtests --fast

# Verbose output
python manage.py runtests --verbose
```

### Test Coverage

Generate detailed coverage reports:

```bash
# Generate coverage report
python manage.py test_coverage

# Coverage with specific targets
python manage.py test_coverage --target 80
```

### Test Data Management

Create test data for development:

```bash
# Create test data
python manage.py create_test_data

# Setup testing environment
python manage.py setup_testing
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [DOCUMENTATION_URL_PLACEHOLDER]
- **Issues**: [GitHub Issues](https://github.com/EyadAmgad/EduMentorAI/issues)
- **Email**: [edumentorai25@gmail.com]


## 🔮 Roadmap

## 📊 Project Stats

- **Languages**: Python, JavaScript, HTML, CSS
- **Framework**: Django 5.x
- **Database**: PostgreSQL
- **AI Models**: LangChain + Sentence Transformers
- **Deployment**: Docker + [Hugging face spaces ](https://huggingface.co/spaces)

---

*Transforming education through artificial intelligence*
