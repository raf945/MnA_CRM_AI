# MnA CRM – Deal Pipeline & LLM Email Assistant

A full‑stack **Mergers & Acquisitions CRM** for managing deal pipelines, organisations and contacts – with an integrated **LLM‑powered email drafting assistant** to speed up outreach and follow‑ups.

Built as a teaching project to practise **production‑style architecture**, **CI/CD**, **containerisation**, and **LLM integration**.

Demo available at: [MnA-CRM-AI](https://mna-crm-ai-610840296940.europe-west1.run.app/login)

**Register a username and password to test!**

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Run Locally](#run-locally)
  - [Run with Docker](#run-with-docker)
- [CI/CD & Deployment](#cicd--deployment)

---

## Overview

MnA CRM is a lightweight web application for **tracking M&A deals**, **managing contacts**, and **recording interactions**, aimed at small corporate finance / advisory teams.

The app also includes an **LLM‑powered chatbot** that acts as an **email drafting assistant**, helping users quickly generate:

- Initial outreach emails to potential targets or buyers  
- Follow‑up emails after meetings  
- Status update summaries for clients or internal stakeholders  

---

## Key Features

- **Deal & pipeline management**
  - Create and manage deals with stages (e.g. Contact, Follow up, Win, Loss)
  - Customised daily task list based on action date
  - View all leads and reschedule.

- **Contact & organisation management**
  - Store basic contact details, name, organisation, action dates
  - View all deals related to a contact or organisation

- **LLM Email Drafting Assistant**
  - Embedded chatbot UI accessible from the CRM
  - Generates draft emails based on:
    - Deal context (e.g. stage, company, value)
    - Contact details (e.g. role, organisation)
    - User‑provided prompt (tone, purpose, key points)
  - Uses the **OpenAI API** under the hood
  - Outputs are editable so users remain in control of final wording

- **Authentication & security** (adjust to match your implementation)
  - Server-side session management
  - Secrets (e.g. OpenAI API key, DB credentials) stored outside the codebase

- **Production‑style delivery**
  - Code in **VS Code** → pushed to **GitHub**
  - **Docker** builds application images
  - Deployed as containers on **Google Cloud Run** behind HTTPS

---

## Architecture

High‑level architecture:

- **Frontend**
  - HTML, CSS, JavaScript
  - Views for pipeline, deal detail, contacts, and the email assistant/chatbot panel

- **Backend**
  - Python backend (e.g. **FastAPI**) exposing RESTful endpoints for:
    - Deals, contacts, organisations, notes
    - LLM email drafting endpoint that calls OpenAI
  - Business logic for pipeline state changes and validation

- **Database**
  - Relational database (e.g. **Cloud SQL** / **Neon PostgreSQL**) for core CRM data
  - ORM / query layer for persistence (adapt to what you use)

- **LLM Integration**
  - Backend endpoint that:
    - Gathers relevant CRM context (deal, contact)
    - Combines it with the user prompt
    - Sends a request to the **OpenAI API**
    - Returns a suggested email draft to the frontend

- **Infrastructure**
  - Application containerised with **Docker**
  - Deployed to **Google Cloud Run**
  - Configuration and secrets managed via environment variables (and Google Secret Manager if used)

---

## Tech Stack

- **Languages:** Python, JavaScript, HTML, CSS  
- **Backend:** FastAPI (or your chosen framework), REST APIs  
- **Frontend:** Vanilla JS / templating (adjust as needed)  
- **Database:** Cloud SQL / Neon PostgreSQL (update to your actual choice)  
- **Cloud & Infra:** Google Cloud Run, Docker, GitHub  
- **LLM:** OpenAI API (chat / completions endpoint)  
- **Tooling:** VS Code, Git & GitHub

---

## Getting Started

### Prerequisites

- Python 3.10+   
- Docker (optional but recommended for parity with production)  
- A Google Cloud project (for Cloud Run / Cloud SQL)  
- An **OpenAI API key**

### Environment Variables

Create a `.env` file in the project root with:

```bash
# Application
APP_ENV=local
SECRET_KEY=your_local_secret_key

# Database
DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname

# NoSQL
MONGODB_URL=your_mongodb_connection_string

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# (Optional) GCP specific
GCP_PROJECT_ID=your_project_id


```

Comment DATABASE_URL, MONGODB_URL and OPENAI_API_KEY and replace with following:
```
DATABASE_URL=os.getenv("DATABASE_URL")
MONGODB_URL=os.getenv("MONGODB_URL")
OPENAI_API_KEY=os.getenv("OPEN_API_KEY")
```

## Run Locally

### 1. Clone the repository
git clone https://github.com/raf945/mna-crm_ai.git
cd mna-crm_ai

### 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate

### 3. Install dependencies
pip install -r requirements.txt

### 4. Run the application (example for FastAPI + Uvicorn)
uvicorn app.main:app --reload

Then visit http://localhost:8000 in your browser.

## Run with Docker

# Build image
docker build -t mna-crm:latest .

# Run container
docker run -p 8000:8000 --env-file .env mna-crm:latest

## CI/CD & Deployment

This project is set up to mimic a production CI/CD flow:

![System Architecture Diagram](https://github.com/raf945/MnA_CRM_AI/raw/main/images/mna_crm_cicd.png)


    1. Development in VS Code

    2. Commit & push code changes to GitHub

    3. Docker image build

        - A Dockerfile defines how the app is containerised

        - (Optional) GitHub Actions workflow builds and pushes the image to a container registry

    4. Deployment to Google Cloud Run

        - New container image is deployed to Cloud Run

        - Service is exposed over HTTPS with autoscaling
