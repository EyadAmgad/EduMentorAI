# Contributing to EduMentorAI

Thank you for your interest in contributing to EduMentorAI! We welcome contributions from the community and are excited to collaborate with you to make this educational platform even better.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## 🤝 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [MAINTAINER_EMAIL_PLACEHOLDER].

### Our Standards

- **Be respectful** and inclusive to all contributors
- **Be constructive** in discussions and feedback
- **Focus on the project** and its educational mission
- **Help newcomers** feel welcome and supported
- **Give credit** where credit is due

## 🚀 Getting Started

### Prerequisites

Before contributing, make sure you have:

- **Python 3.9+** (recommended: 3.12)
- **Git** for version control
- **Basic Django knowledge** for backend contributions
- **Understanding of AI/ML concepts** for RAG-related features
- **Familiarity with JavaScript/CSS** for frontend contributions

### First Time Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EduMentorAI.git
   cd EduMentorAI
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/EyadAmgad/EduMentorAI.git
   ```
4. **Follow the installation guide** in the README.md

## 🛠️ How to Contribute

### Types of Contributions

We welcome various types of contributions:

- 🐛 **Bug fixes**
- ✨ **New features**
- 📚 **Documentation improvements**
- 🧪 **Testing enhancements**
- 🎨 **UI/UX improvements**
- 🚀 **Performance optimizations**
- 🌐 **Internationalization**
- 📱 **Accessibility improvements**

### Good First Issues

Look for issues labeled with:
- `good first issue` - Perfect for newcomers
- `help wanted` - Community help needed
- `documentation` - Documentation improvements
- `frontend` - UI/UX related tasks
- `backend` - Django/Python related tasks

## 💻 Development Setup

### Environment Setup

1. **Create development environment**:
   ```bash
   conda create -n edumetor-dev python=3.12 -y
   conda activate edumetor-dev
   ```

2. **Install dependencies**:
   ```bash
   cd src
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with development settings
   ```

5. **Setup database**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**:
   ```bash
   python manage.py test
   pytest  # If using pytest
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## 📏 Coding Standards

### Python Code Style

We follow **PEP 8** with some project-specific guidelines:

- **Line length**: Maximum 88 characters (Black formatter)
- **Imports**: Use absolute imports, group by standard/third-party/local
- **Naming**: Use descriptive names, snake_case for functions/variables
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

#### Example Code Style

```python
from typing import List, Optional
from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    """Model for storing uploaded educational documents.
    
    Attributes:
        title: Human-readable document title
        file: Uploaded file field
        uploaded_by: User who uploaded the document
        created_at: Timestamp of document creation
    """
    
    title: str = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_by: User = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_file_size(self) -> int:
        """Get file size in bytes.
        
        Returns:
            File size in bytes, 0 if file doesn't exist.
        """
        return self.file.size if self.file else 0
    
    def __str__(self) -> str:
        return f"{self.title} by {self.uploaded_by.username}"
```

### Frontend Code Style

- **JavaScript**: Use ES6+ features, prefer `const`/`let` over `var`
- **CSS**: Use BEM methodology for class naming
- **HTML**: Semantic HTML5 elements, proper accessibility attributes

### Git Commit Convention

We use **Conventional Commits** for clear commit history:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(chat): add real-time message streaming
fix(auth): resolve email verification bug
docs(readme): update installation instructions
test(models): add Document model tests
```

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test rag_app

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Writing Tests

- **Unit tests**: Test individual functions/methods
- **Integration tests**: Test component interactions
- **API tests**: Test REST API endpoints
- **UI tests**: Test user interface functionality

#### Example Test

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rag_app.models import Document, Subject


class DocumentModelTest(TestCase):
    """Test cases for Document model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.subject = Subject.objects.create(
            name='Computer Science',
            code='CS101',
            created_by=self.user
        )
    
    def test_document_creation(self):
        """Test document creation with valid data."""
        document = Document.objects.create(
            title='Test Document',
            subject=self.subject,
            uploaded_by=self.user
        )
        
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(str(document), 'Test Document by testuser')
```

## 📝 Pull Request Process

### Before Submitting

1. **Update your fork**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Rebase your feature branch**:
   ```bash
   git checkout feature/your-feature
   git rebase main
   ```

3. **Run tests and linting**:
   ```bash
   python manage.py test
   flake8 .
   black --check .
   ```

### PR Requirements

- ✅ **Clear description** of changes and motivation
- ✅ **Tests** for new functionality
- ✅ **Documentation** updates if needed
- ✅ **No merge conflicts** with main branch
- ✅ **Follows coding standards**
- ✅ **Passes all CI checks**

### PR Template

```markdown
## Description
Brief description of changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
```

## 🐛 Issue Guidelines

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** for known solutions
3. **Update to latest version** if possible

### Bug Reports

Include:
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, browser)
- **Error messages** and stack traces
- **Screenshots** if applicable

### Feature Requests

Include:
- **Clear description** of the feature
- **Use case** and motivation
- **Proposed implementation** (if you have ideas)
- **Alternatives considered**

## 📚 Documentation

### Documentation Types

- **Code documentation**: Inline comments and docstrings
- **API documentation**: REST API endpoint documentation
- **User guides**: How-to guides for end users
- **Developer guides**: Technical documentation for contributors

### Writing Guidelines

- **Clear and concise** language
- **Step-by-step instructions** where applicable
- **Code examples** for technical concepts
- **Screenshots** for UI-related documentation
- **Keep it updated** with code changes

## 🌟 Recognition

We appreciate all contributions! Contributors will be:

- **Listed in CONTRIBUTORS.md**
- **Mentioned in release notes** for significant contributions
- **Given appropriate GitHub repository permissions** for regular contributors

## 🆘 Getting Help

### Resources

- **Documentation**: Check the README.md and docs/
- **GitHub Issues**: Browse existing issues and discussions
- **Discord/Slack**: [COMMUNITY_CHAT_PLACEHOLDER]
- **Email**: [MAINTAINER_EMAIL_PLACEHOLDER]

### Questions

Don't hesitate to ask questions! We prefer:

1. **GitHub Discussions** for general questions
2. **GitHub Issues** for bug reports and feature requests
3. **Direct contact** for sensitive matters

## 📞 Contact

- **Project Maintainer**: [EyadAmgad](https://github.com/EyadAmgad)
- **Email**: [MAINTAINER_EMAIL_PLACEHOLDER]
- **Discord**: [DISCORD_LINK_PLACEHOLDER]

---

Thank you for contributing to EduMentorAI! Together, we're building a better educational future powered by AI. 🚀

*Happy coding!* 💻✨
