# SEM/MIDS Answers Generator

An AI-powered web application that extracts questions from PDF documents and generates detailed answers using LLMs for SEM/MIDS exam preparation.

## Features

- **Question Extraction**: Upload question papers in PDF format and automatically extract questions.
- **Multiple Reference Notes**: Upload multiple reference materials to improve answer quality.
- **LLM-Powered Answers**: Utilizes Google's Gemini API with OpenAI as backup for detailed answers.
- **Customization Options**:
  - **Subject Name**: Specify the subject for proper formatting and context.
  - **Mark Type**: Choose between 5 or 8 mark questions to adjust answer length.
  - **Study Mode**: Select between "Understanding" or "Memorize" for different learning styles.
- **Downloadable Formats**: Get answers in both DOCX and PDF formats.
- **History Tracking**: Access previously processed requests through history page.

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Gemini API key (primary)
- OpenAI API key (backup)

### Environment Setup

1. Copy `.env.example` to `.env` and fill in the required credentials:
   ```
   cp .env.example .env
   ```

2. Add your API keys and database connection string:
   ```
   # API Keys
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   
   # Database Configuration
   DATABASE_URL=postgresql://username:password@host:port/database
   
   # Flask Configuration
   FLASK_SECRET_KEY=your_secret_key
   SESSION_SECRET=your_session_secret
   ```

### Installation

1. Install required packages:
   ```
   pip install -r requirements.txt
   ```

2. Start the application:
   ```
   python main.py
   ```

### Deployment

This application can be deployed on platforms like Render.com. See the `RENDER_DEPLOYMENT.md` file for detailed instructions.

## Usage

1. Access the application at http://localhost:5000
2. Upload a question paper PDF
3. (Optional) Upload reference notes
4. Enter subject name
5. Select mark type and study mode
6. Click Process to generate answers
7. Download results in your preferred format
8. Access previously generated documents through the History page

## Credits

Developed for MRU B.Tech Students
Author: Mohammed Abdullah