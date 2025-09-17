# SaveMyLinks

**AI For Developers II Capstone Project | [ALX](https://www.alxafrica.com/)**

## 🔖 Project Description

**SaveMyLinks** is a public-facing web application designed to curate and share valuable online resources. It addresses information overload by offering a clean, organized, and visually simple dashboard for storing and discovering useful links across the internet. This project serves as a capstone for the ALX AI For Developers II course, demonstrating practical integration of AI tools throughout the development lifecycle.

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Jinja2 Templates, Bulma CSS
- **Database:** SQLite (Development), PostgreSQL (Production)
- **Hosting:** Railway
- **AI Tooling:** Trae IDE, CodeRabbit

---

## 🧠 AI Integration Strategy

### 1. Code and Feature Generation
Using **Trae IDE**, AI will generate foundational code based on high-level prompts. Example prompt:
> "Generate a FastAPI endpoint at `/api/resources/` using SQLAlchemy and Pydantic that returns all saved links in JSON format."

### 2. Testing Support
AI will assist in writing unit and integration tests via **pytest**. Example prompt:
> "Write a test for the GET /api/resources/ endpoint that checks the response status code and JSON structure."

### 3. Documentation
- **Code Documentation:** AI will generate docstrings in Google style for all functions and classes.
- **READMEs:** AI will assist in maintaining clear and updated project documentation.
- **API Docs:** FastAPI’s built-in `/docs` endpoint will provide interactive API documentation.

### 4. Context-Aware Development
Rule files located in `.trae/rules/` (e.g., `architecture.md`, `development.md`) provide Trae with project-specific conventions, ensuring consistent and context-aware code generation.

### 5. In-Editor and PR Review Tooling
- **Trae IDE:** Used for real-time AI-assisted coding and prompt-driven development.
- **CodeRabbit:** Provides AI-powered code review and automated PR summaries.

---

## 📁 Project Structure

```
savemylinks/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── routes/
│   │   └── resources.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── add.html
│   └── tests/
│       ├── __init__.py
│       └── test_routes.py
├── .trae/
│   └── rules/
│       ├── architecture.md
│       ├── development.md
│       ├── orchestration.md
│       └── design_philosophy.md
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd savemylinks
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open your browser and navigate to `http://localhost:8000`

---

## 📌 Future Enhancements
- User authentication and private collections
- Tags and advanced filtering
- Link preview image generation
- Public API for third-party access

---

This project was developed as part of the **AI For Developers II** course offered by [ALX](https://www.alxafrica.com/), focusing on real-world AI-assisted development practices.