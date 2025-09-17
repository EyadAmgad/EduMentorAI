# EduMentorAI - AI-Powered Educational Platform

A modern Django web application that provides AI-powered learning assistance with document upload, intelligent chat, and quiz generation capabilities.

## 🚀 Features

- **Smart Document Upload**: Upload PDFs, Word docs, PowerPoints, and text files
- **AI Chat Assistant**: Ask questions about your study materials and get intelligent responses
- **Quiz Generation**: Generate personalized quizzes from your documents
- **Progress Tracking**: Monitor your learning progress with detailed analytics
- **Modern UI**: ChatGPT-inspired interface with responsive design
- **Supabase Integration**: Professional database, authentication, and file storage

## 🛠 Technology Stack

- **Backend**: Django 5.2.4, Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Database**: PostgreSQL (via Supabase) with SQLite fallback
- **Storage**: Supabase Storage with local fallback
- **Authentication**: Django Allauth
- **AI Integration**: Ready for RAG implementation

## 📋 Prerequisites

- Python 3.12+
- pip (Python package manager)
- Virtual environment (recommended)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd EduMentorAI/src
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv penv
   source penv/bin/activate  # On Windows: penv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup** (Optional)
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main app: http://localhost:8000
   - Admin panel: http://localhost:8000/admin

## 🔧 Configuration

### Supabase Setup (Production)

1. Create a Supabase project at https://supabase.com
2. Get your project URL and anon key
3. Create a storage bucket for file uploads
4. Update your `.env` file:
   ```
   SUPABASE_URL=your-project-url
   SUPABASE_KEY=your-anon-key
   SUPABASE_BUCKET=your-bucket-name
   ```

### Email Configuration (Optional)

For user registration emails, configure SMTP in `.env`:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🎨 User Interface

The application features a modern, ChatGPT-inspired design with:

- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Modern Color Scheme**: Green primary colors with clean aesthetics
- **Interactive Elements**: Hover effects, smooth transitions
- **Professional Typography**: Inter font family
- **Intuitive Navigation**: Clear menu structure and breadcrumbs

## 🔒 Security Features

- CSRF protection
- SQL injection prevention
- XSS protection
- Secure file upload handling
- User authentication and authorization
- Environment-based configuration

## 📊 Current Status

✅ **Completed:**
- Django project setup with professional architecture
- Modern, responsive UI with ChatGPT-inspired design
- User authentication and profile management
- Database models for educational platform
- Supabase integration for production deployment
- Document upload system
- Basic chat interface
- Quiz system foundation

⚠️ **In Progress:**
- RAG (Retrieval-Augmented Generation) implementation
- AI-powered document processing
- Interactive chat functionality

🔮 **Planned:**
- Complete AI integration
- Real-time chat features
- Advanced analytics
- Mobile responsiveness improvements

## 🚀 Deployment

The application is ready for deployment with:
- Supabase backend integration
- Environment-based configuration
- Production-ready Django settings
- Static file handling
- Security best practices

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the documentation
- Open an issue on GitHub
- Contact the development team
