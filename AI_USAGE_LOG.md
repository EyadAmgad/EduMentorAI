## Generative AI Usage Log

This log documents specific instances of Generative AI tool usage throughout the development of the EduMentorAI project.

---

### Feature: Core Django Setup & Configuration

#### **Task: Configuring Django Settings for Production**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I need to configure my Django `settings.py` for a production environment. I'm using whitenoise for static files and need to set up environment variables for my `SECRET_KEY` and `DEBUG` status. Can you show me how to do this?"
    >
    > **ChatGPT-4:** "Certainly. You can use the `os` library to get environment variables. Here's how you can configure your `settings.py`:"
    > ```python
    > import os
    > from decouple import config
    >
    > # ...
    > SECRET_KEY = config('SECRET_KEY')
    > DEBUG = config('DEBUG', default=False, cast=bool)
    > # ...
    > STATIC_URL = '/static/'
    > STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    > STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    > ```

* **Reflection on AI's Assistance:**
    ChatGPT-4 provided a clear and secure way to manage production settings. This saved time and helped in avoiding common configuration mistakes, ensuring a smoother deployment process.

#### **Task: Implementing Email Verification Middleware**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to create a middleware in Django that checks if a user's email is verified. If it's not verified, I want to redirect them to a page that prompts them to verify their email. Can you provide the code for this middleware?"
    >
    > **Gemini:** "Certainly. Here is an `EmailVerificationMiddleware` that you can add to your `MIDDLEWARE` settings. It checks if the user is authenticated and if their email is verified. If not, it redirects them to an `email_verification_required` page."

* **AI's Response (Summary from `email_verification_middleware.py`):**
    The AI provided a complete middleware class that checks for email verification on each request. It included logic to exclude certain URLs from the check, such as the login, signup, and logout pages, to avoid redirect loops.

* **Reflection on AI's Assistance:**
    This was a crucial security and user experience feature that would have taken a significant amount of time to implement from scratch. The AI-generated middleware was well-structured and easy to integrate into the project.

---

### Feature: User Authentication & Profile Management

#### **Task: Creating a Custom User Signup Form**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to create a custom signup form in Django that includes fields for `first_name`, `last_name`, `email`, and a `user_type` with choices for 'Student' and 'Teacher'. How can I do this using `django-allauth`?"
    >
    > **Gemini:** "You can create a custom form that inherits from `SignupForm` and add your custom fields. Here's an example:"
    > ```python
    > from allauth.account.forms import SignupForm
    > from django import forms
    >
    > class CustomSignupForm(SignupForm):
    >     USER_TYPE_CHOICES = (
    >         ("student", "Student"),
    >         ("teacher", "Teacher"),
    >     )
    >     user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES)
    >     first_name = forms.CharField(max_length=30, label='First Name')
    >     last_name = forms.CharField(max_length=30, label='Last Name')
    >
    >     def save(self, request):
    >         user = super(CustomSignupForm, self).save(request)
    >         user.user_type = self.cleaned_data['user_type']
    >         user.first_name = self.cleaned_data['first_name']
    >         user.last_name = self.cleaned_data['last_name']
    >         user.save()
    >         return user
    > ```

* **Reflection on AI's Assistance:**
    This saved a significant amount of time that would have been spent reading through the `django-allauth` documentation. The generated code was easy to understand and integrate into the project.

---

### Feature: RAG Pipeline

#### **Task: Developing the `data_processor.py` script**
* **Generative AI Tool Used:** Gemini
* **Conversation:**
    > **Developer:** "I need a Python class called `DataProcessor` that can handle different document types. Specifically, I need to load and split `.pdf`, `.txt`, and `.pptx` files. Can you provide the code for this class, using the `langchain` library for document loading and splitting?"
    >
    > **Gemini:** "Certainly. Here is a `DataProcessor` class that uses `PyPDFLoader`, `TextLoader`, and `UnstructuredPowerPointLoader` from `langchain` to handle the different file types. It also includes a method to split the documents into chunks using `RecursiveCharacterTextSplitter`."
    >
    > ```python
    > from langchain.text_splitter import RecursiveCharacterTextSplitter
    > from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredPowerPointLoader
    >
    > class DataProcessor:
    >     def __init__(self, chunk_size=1000, chunk_overlap=200):
    >         self.text_splitter = RecursiveCharacterTextSplitter(
    >             chunk_size=chunk_size, chunk_overlap=chunk_overlap
    >         )
    >
    >     def load_and_split_document(self, file_path):
    >         if file_path.endswith(".pdf"):
    >             loader = PyPDFLoader(file_path)
    >         elif file_path.endswith(".txt"):
    >             loader = TextLoader(file_path)
    >         elif file_path.endswith(".pptx"):
    >             loader = UnstructuredPowerPointLoader(file_path)
    >         else:
    >             raise ValueError(f"Unsupported file type: {file_path}")
    >
    >         documents = loader.load()
    >         return self.text_splitter.split_documents(documents)
    > ```
* **Reflection on AI's Assistance:**
    This saved approximately 2-3 hours of development time that would have been spent researching and implementing the different loaders and text splitters from the `langchain` library. The AI-generated code was clean, efficient, and directly applicable to the project's needs.

#### **Task: Building the `SlideProcessor.py` script**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I need to create a Python script that generates Google Slides from a given text. The script should use the Google Slides API. Can you provide a class structure for a `SlideProcessor` that can authenticate with the API and create a presentation with a title and content slides?"
    >
    > **ChatGPT-4:** "Of course. Here is a `SlideProcessor` class that handles authentication using a service account and has methods to create a presentation and add slides with titles and content."

* **AI's Response (Summary from `SlideProcessor.py`):**
    The AI provided a `SlideProcessor` class with methods for:
    * **`__init__`**: Authenticating with the Google Slides API using credentials from a JSON file.
    * **`create_presentation`**: Creating a new presentation with a given title.
    * **`add_slide`**: Adding a new slide to a presentation with a specified title and content.
* **Reflection on AI's Assistance:**
    The AI-generated code provided a solid foundation for the `SlideProcessor`, saving a lot of time that would have been spent on understanding the Google Slides API and its authentication process.

#### **Task: Developing the `embeddings.py` and `vectorstore.py` scripts**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I'm building a RAG pipeline and I need to create classes for handling embeddings and the vector store. For the embeddings, I want to use a pre-trained model from Hugging Face. For the vector store, I'll be using FAISS. Can you provide the Python code for these two classes?"
    >
    > **ChatGPT-4:** "Of course. Here is an `EmbeddingModel` class that loads a sentence transformer model from Hugging Face and an `VectorStore` class that uses FAISS to create and manage a vector index from the document chunks."

* **AI's Response (Summary from `embeddings.py` and `vectorstore.py`):**
    * **`embeddings.py`:** The AI provided a class that initializes a pre-trained sentence transformer model and has a method to create embeddings from text chunks.
    * **`vectorstore.py`:** The AI generated a class that takes the document chunks and the embedding model as input, creates a FAISS index, and has methods to save and load the index from disk.

* **Reflection on AI's Assistance:**
    This saved several hours of development time. The AI-generated code provided a clean and efficient implementation of the embedding and vector store components, which are the core of the RAG pipeline.

#### **Task: Implementing the Retriever and Generative Model**
* **Generative AI Tool Used:** GitHub Copilot
* **Conversation:**
    *(The developer is working on `retriever.py` and `model.py` and starts typing the class definitions.)*

    > **Developer's Code in `retriever.py`:**
    > ```python
    > class Retriever:
    >     def __init__(self, vector_store, embedding_model):
    >         self.vector_store = vector_store
    >         self.embedding_model = embedding_model
    >
    >     def retrieve_documents(self, query, n_results=5):
    > ```
    > **GitHub Copilot Suggestion:**
    > ```python
    >         query_embedding = self.embedding_model.create_embeddings([query])
    >         distances, indices = self.vector_store.search(query_embedding, k=n_results)
    >         return [self.vector_store.get_document(i) for i in indices[0]]
    > ```
    > **Developer's Code in `model.py`:**
    > ```python
    > from langchain_community.llms import HuggingFaceHub
    >
    > class GenerativeModel:
    >     def __init__(self, model_name="google/flan-t5-large"):
    > ```
    > **GitHub Copilot Suggestion:**
    > ```python
    >         self.llm = HuggingFaceHub(
    >             repo_id=model_name,
    >             model_kwargs={"temperature": 0.1, "max_length": 512}
    >         )
    >
    >     def generate_response(self, context, query):
    >         prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
    >         return self.llm(prompt)
    > ```

* **Reflection on AI's Assistance:**
    GitHub Copilot was instrumental in autocompleting the core logic for the retriever and the generative model. It correctly inferred the required steps for retrieving documents from the vector store and for generating a response with the language model, significantly speeding up the development process.

---

### Feature: Document & Subject Management

#### **Task: Creating Django Models for Subjects and Documents**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to create Django models for `Subject` and `Document`. A `Subject` can have multiple `Documents`, and each `Document` should be associated with a user. Can you provide the model definitions?"
    >
    > **Gemini:** "Here are the Django model definitions for `Subject` and `Document`:"
    > ```python
    > from django.db import models
    > from django.contrib.auth.models import User
    >
    > class Subject(models.Model):
    >     user = models.ForeignKey(User, on_delete=models.CASCADE)
    >     name = models.CharField(max_length=255)
    >
    >     def __str__(self):
    >         return self.name
    >
    > class Document(models.Model):
    >     subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    >     file = models.FileField(upload_to='documents/')
    >     uploaded_at = models.DateTimeField(auto_now_add=True)
    >
    >     def __str__(self):
    >         return self.file.name
    > ```

* **Reflection on AI's Assistance:**
    This was a quick and easy way to generate the boilerplate code for the models, saving time and ensuring the relationships between the models were set up correctly from the start.

---

### Feature: Core Application Logic (Views)

#### **Task: Creating Class-Based Views for Dashboard and Chat**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to create a `DashboardView` that displays a list of subjects and a `ChatView` that handles the chat logic. Both should be class-based views and require the user to be logged in. Can you provide the code for these views?"
    >
    > **Gemini:** "Certainly. Here is a `DashboardView` that inherits from `LoginRequiredMixin` and `ListView` to display the subjects, and a `ChatView` that handles both GET and POST requests for the chat interface."

* **AI's Response (Summary from `views.py`):**
    * **`DashboardView`:** The AI provided a `DashboardView` that correctly queries the `Subject` model for the current user's subjects and passes them to the template.
    * **`ChatView`:** The AI generated a `ChatView` that handles the initial rendering of the chat page and the POST requests containing user messages. It also included logic for interacting with the RAG pipeline to get a response.

* **Reflection on AI's Assistance:**
    This saved a significant amount of time that would have been spent on writing boilerplate code for class-based views. The generated code was clean, followed Django best practices, and was easy to customize.

#### **Task: Implementing CRUD Views for Subjects and Documents**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I need to create function-based views for CRUD operations on my `Subject` and `Document` models. This includes creating, updating, and deleting subjects, as well as uploading and deleting documents. All views should be protected with the `@login_required` decorator."
    >
    > **ChatGPT-4:** "Of course. Here are the CRUD views for your `Subject` and `Document` models, complete with form handling and login protection."

* **AI's Response (Summary from `views.py`):**
    The AI provided a complete set of function-based views for:
    * `subject_create`, `subject_update`, `subject_delete`: For creating, editing, and deleting subjects.
    * `document_upload`, `document_delete`: For uploading and deleting documents associated with a subject.
    All views included the `@login_required` decorator to ensure only authenticated users could access them.

* **Reflection on AI's Assistance:**
    This was a huge time-saver. The AI generated all the necessary views for managing subjects and documents, including form validation and database operations. This allowed the developer to focus on the more complex aspects of the application.

---

### Feature: Frontend Development

#### **Task: Designing the Dashboard Layout**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to create a dashboard layout with a sidebar for navigation and a main content area. The sidebar should have links to the dashboard, subjects, and profile. The main content area should display a welcome message and a grid of the user's subjects. Can you provide the HTML and CSS for this?"
    >
    > **Gemini:** "Here is the HTML structure for your dashboard, including a responsive sidebar and a main content area with a grid for your subjects. I've also included some modern and clean CSS to style the layout."

* **AI's Response (Summary from `dashboard.html` and `dashboard.css`):**
    The AI generated a responsive two-column layout. The sidebar was styled with a dark background and clear navigation links. The main content area used a CSS grid to display subject cards, each with a title and a link to view the subject's documents.

* **Reflection on AI's Assistance:**
    This saved several hours of frontend development time. The AI-generated layout was professional, responsive, and provided a great starting point for the dashboard design.

#### **Task: Creating an Animated File Upload Form**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I want to create a file upload form with a drag-and-drop area. When a file is dragged over the area, it should be highlighted. I also want a progress bar that updates as the file is being uploaded. Can you provide the HTML, CSS, and JavaScript for this?"
    >
    > **ChatGPT-4:** "Certainly. Here is the code for a file upload form with a drag-and-drop area. The JavaScript includes event listeners for the drag-and-drop functionality and an `XMLHttpRequest` to handle the file upload with a progress bar."

* **AI's Response (Summary from `document_upload.html`, `document_upload.css`, and `document_upload.js`):**
    The AI provided a complete file upload component. The CSS included styles for the drag-and-drop area, including a "dragover" class to provide visual feedback. The JavaScript handled the file selection, drag-and-drop events, and the asynchronous file upload with a progress bar.

* **Reflection on AI's Assistance:**
    This was a complex frontend feature that would have taken a lot of time to implement from scratch. The AI-generated code was well-structured and included all the necessary logic for a modern and user-friendly file upload experience.

#### **Task: Implementing JavaScript for the Quiz Interface**
* **Generative AI Tool Used:** GitHub Copilot
* **Conversation:**
    *(The developer is working on the `quiz.js` file and needs to write a function to handle the user's answer selection and provide feedback.)*

    > **Developer's Code:**
    > ```javascript
    > function selectAnswer(selectedOption, correctAnswer) {
    >     const options = document.querySelectorAll('.option');
    >     options.forEach(option => {
    >         option.removeEventListener('click', selectAnswer);
    >         if (option.textContent === correctAnswer) {
    > ```
    > **GitHub Copilot Suggestion:**
    > ```javascript
    >             option.classList.add('correct');
    >         } else if (option === selectedOption) {
    >             option.classList.add('incorrect');
    >         }
    >     });
    >
    >     // Move to the next question after a delay
    >     setTimeout(nextQuestion, 1000);
    > }
    > ```

* **Reflection on AI's Assistance:**
    GitHub Copilot was very helpful in autocompleting the logic for providing feedback to the user. It correctly inferred the need to add "correct" and "incorrect" classes to the options and to move to the next question after a short delay.

---

### Feature: Testing

#### **Task: Writing Unit Tests for Views, Models, and Forms**
* **Generative AI Tool Used:** Gemini
* **Conversation:**

    > **Developer:** "I need to write unit tests for my Django app. Can you provide examples of how to test the views, models, and forms? For the views, I want to test that they return the correct status code and use the right template. For the models, I want to test their creation and string representation. For the forms, I want to test their validation."
    >
    > **Gemini:** "Certainly. Here are examples of how to write tests for your views, models, and forms using Django's `TestCase`."

* **AI's Response (Summary from `tests` directory):**
    * **`test_views.py`:** The AI provided test cases that checked if the views were accessible only to logged-in users, returned a 200 status code, and used the correct templates.
    * **`test_models.py`:** The AI generated tests that verified the correct creation of `Subject` and `Document` objects and checked their `__str__` methods.
    * **`test_forms.py`:** The AI provided tests for the `SubjectForm` and `DocumentForm` that checked for valid and invalid form submissions.

* **Reflection on AI's Assistance:**
    This was incredibly helpful for ensuring the quality and reliability of the application. The AI-generated tests provided a solid foundation for the test suite and saved a lot of time that would have been spent on writing repetitive test code.

---

### Feature: Deployment & Management

#### **Task: Creating a Dockerfile and Management Command**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**

    > **Developer:** "I need to create a `Dockerfile` for my Django application and a management command to create test data. The `Dockerfile` should set up a Python environment, install the dependencies, and run the Django server. The management command should create a test user, a subject, and a document."
    >
    > **ChatGPT-4:** "Here is a `Dockerfile` for your Django application and a `create_test_data` management command."

* **AI's Response (Summary):**
    * **`Dockerfile`:** The AI provided a multi-stage `Dockerfile` that built the application in a separate stage to keep the final image size small. It included instructions for installing dependencies, copying the source code, and running the application with Gunicorn.
    * **`create_test_data.py`:** The AI generated a management command that created a test user, a subject, and a document, making it easy to populate the database for testing and development.

* **Reflection on AI's Assistance:**
    This saved a significant amount of time on deployment and data management tasks. The `Dockerfile` provided a reproducible environment for the application, and the management command made it easy to set up the application for testing.

---
### Feature: Quiz Generation

#### **Task: Creating the quiz generation logic**
* **Generative AI Tool Used:** ChatGPT-4
* **Conversation:**
    > **Developer:** "I need to generate a multiple-choice quiz from a given text. Please write a Python function that takes a text block and the number of questions as input. The function should use a generative model to create the quiz and return it as a JSON object. Each question should have a 'question', a list of 'options', and the 'correct_answer'."

    > **ChatGPT-4:** "Here's a function that uses a prompt to instruct a large language model to generate a quiz in the specified JSON format. It also includes a loop to retry parsing the JSON in case of formatting errors from the model."

* **AI's Response (Summary from `quiz_generator.py`):**
    The AI provided a Python script containing a `QuizGenerator` class with a `generate_quiz` method. This method constructs a detailed prompt for a language model, asking it to generate a quiz from the provided text and format the output as a JSON object. The script also includes a `Quiz` data class to structure the quiz data.
* **Reflection on AI's Assistance:**
    This task would have been extremely challenging to implement without a generative AI. The AI's ability to understand the context of the document and generate relevant questions and answers was the core of this feature. This saved a significant amount of time and made the quiz generation feature possible.

---

### Feature: Frontend Development

#### **Task: Writing CSS for the chat interface**
* **Generative AI Tool Used:** GitHub Copilot
* **Conversation:**
    *(The developer is working on the `chat.css` file and starts typing the styles for the message bubbles.)*

    > **Developer's Code:**
    > ```css
    > .user-message {
    >     align-self: flex-end;
    >     background-color: #007bff;
    >     color: white;
    > ```
    > **GitHub Copilot Suggestion:**
    > ```css
    >     border-radius: 15px 15px 0 15px;
    >     margin-right: 10px;
    > }
    >
    > .bot-message {
    >     align-self: flex-start;
    >     background-color: #f1f1f1;
    >     color: #333;
    >     border-radius: 15px 15px 15px 0;
    >     margin-left: 10px;
    > }
    > ```
* **Reflection on AI's Assistance:**
    GitHub Copilot was incredibly helpful in speeding up the process of writing CSS. It anticipated the required styles for both user and bot messages, including the `border-radius` for the bubble effect and the alignment. This saved time and effort, allowing the developer to focus on the overall layout and design.

---

### Feature: Documentation

#### **Task: Authored the `README.md` file**
* **Generative AI Tool Used:** Gemini
* **Conversation:**
    > **Developer:** "I need to create a `README.md` file for my Django project, 'EduMentorAI'. It's an educational tool that uses a RAG pipeline for chatting with documents, generating quizzes, and creating slides. Can you write a `README.md` with sections for 'About', 'Features', 'Getting Started' with installation instructions, and 'Usage'?"

    > **Gemini:** "Here is a comprehensive `README.md` file tailored to your project. It includes all the sections you requested, with placeholders for you to add more specific details. The 'Getting Started' section includes the necessary commands to set up and run the Django project."
* **AI's Response (Summary from `README.md`):**
    The AI generated a well-structured `README.md` file that included:
    * A brief introduction to the project.
    * A list of key features (Document Upload, Chat with Documents, Quiz Generation, Slide Generation).
    * A "Getting Started" guide with instructions for cloning the repository, installing dependencies, setting up the environment, and running the application.
    * A "Usage" section explaining how to use the different features of the application.
* **Reflection on AI's Assistance:**
    Gemini provided a professional and well-organized `README.md` file that served as a great starting point. This saved at least an hour of writing and formatting, and the resulting documentation was clear and easy to follow for new developers joining the project.