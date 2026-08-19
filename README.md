# 🧠 Candidate Intelligence Platform

> An **AI-powered talent intelligence platform** built with **Django REST Framework** + **React (Vite)**. Ingest candidate data from CSVs and PDF/DOCX resumes, enrich profiles with **Gemini LLM**, run **semantic search** via MongoDB vector embeddings, and view everything through a stunning dark glassmorphism dashboard.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Django-4.2%2B-green?style=for-the-badge&logo=django" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react" />
  <img src="https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite" />
  <img src="https://img.shields.io/badge/LangChain-0.3-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Gemini-1.5_Flash-purple?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-brightgreen?style=for-the-badge&logo=mongodb" />
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔀 **Multi-Source Deduplication** | Upload a CSV and a PDF for the same person — the platform matches on email/phone and merges them into one enriched profile. |
| 🤖 **Gemini LLM Extraction** | Structured data extraction from raw resume text using `gemini-1.5-flash` and `with_structured_output` (Pydantic schema-guaranteed JSON). |
| 🔍 **RAG Semantic Search** | Natural language queries over candidates using `all-MiniLM-L6-v2` embeddings + cosine similarity stored in MongoDB. |
| 📊 **Provenance & Confidence** | Every field tracks its source (CSV / Resume / LLM), extraction method, and a trust score. |
| 🗄️ **100% MongoDB Backed** | Candidate profiles AND resume chunk embeddings all live in MongoDB — no secondary vector database. |
| 🖥️ **Modern React Dashboard** | Dark glassmorphism UI with sidebar navigation, slide-out candidate detail drawers, drag-and-drop uploads, and semantic search. |

---

## 🏗️ Architecture

```
CSV / PDF / DOCX / TXT
        │
        ▼
┌─────────────────────┐
│  LangChain Loaders  │  PyPDFLoader, TextLoader, Docx2txtLoader
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────┐
│  Section-Aware Text Splitting│  RecursiveCharacterTextSplitter → chunks
└─────────┬───────────────────┘
          │
          ▼
┌────────────────────────────┐
│  MongoDB Vector Store       │  MiniLM embeddings → cosine similarity search
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│   Candidate Merger          │  Email/phone identity resolution + dedup
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│  Gemini LLM Extraction      │  RAG context → structured Pydantic schema
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────┐
│  Django REST API (port 8000)  ←→  Vite React UI (port 3000) │
└────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 4.2+ · Django REST Framework |
| **Frontend** | Vite 5 · React 18 · React Router 6 · Lucide Icons |
| **LLM** | Google Gemini 1.5 Flash (`langchain-google-genai`) |
| **Embeddings** | `all-MiniLM-L6-v2` via `sentence-transformers` (local, free) |
| **Vector Store** | MongoDB with manual cosine similarity |
| **AI Framework** | LangChain 0.3 (LCEL chains, `with_structured_output`) |
| **Database** | MongoDB Atlas (PyMongo + certifi for TLS) |
| **Data Validation** | Pydantic v2 |

---

## 📂 Project Structure

```
candidate_platform_django/
│
├── backend/                        # Django project root
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example                # ← Copy to .env and fill in keys
│   │
│   ├── config/                     # Django settings & routing
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── candidates/                 # Django app — all API endpoints
│   │   ├── views.py                # 11 DRF APIView endpoints
│   │   └── urls.py
│   │
│   ├── models/                     # Pydantic data models
│   │   └── candidate.py            # Candidate, Skill, Experience, Education …
│   │
│   ├── pipeline/                   # Core processing pipeline
│   │   ├── merger/merge.py         # CandidateMerger — dedup + field merging
│   │   ├── confidence/             # Per-field confidence scoring & explainer
│   │   ├── normalizers/            # Phone (E.164), skill canonicalization, dates
│   │   └── parsers/recruiter_csv.py# Flexible CSV parser
│   │
│   ├── lc/                         # LangChain AI layer
│   │   ├── llm.py                  # ChatGoogleGenerativeAI factory
│   │   ├── embeddings.py           # SentenceTransformer / Gemini switcher
│   │   ├── loaders.py              # PDF, DOCX, TXT document loaders
│   │   ├── section_splitter.py     # Section-aware resume chunking
│   │   ├── mongo_vectorstore.py    # Chunk indexing + cosine search in MongoDB
│   │   ├── extractor.py            # Pydantic schema + Gemini structured extraction
│   │   ├── retriever.py            # RAG context builder
│   │   └── conflict_resolver.py    # LLM-based field conflict resolution
│   │
│   └── api/                        # Storage layer
│       └── mongo_storage.py        # PyMongo CRUD — MongoStorage class
│
└── frontend/                       # Vite + React 18
    ├── src/
    │   ├── App.jsx                  # Routes + layout shell
    │   ├── index.css                # Dark glassmorphism design system
    │   ├── contexts/
    │   │   ├── CandidateContext.jsx # Global candidate state + API calls
    │   │   ├── DrawerContext.jsx    # Slide-out drawer state
    │   │   └── ToastContext.jsx     # Toast notification system
    │   ├── components/
    │   │   ├── Sidebar.jsx          # Navigation sidebar with live stats
    │   │   ├── Topbar.jsx           # Top header bar
    │   │   ├── CandidateCard.jsx    # Card with avatar, skills, confidence bar
    │   │   └── CandidateDrawer.jsx  # Profile / Confidence / Provenance tabs
    │   └── pages/
    │       ├── Dashboard.jsx        # Candidate grid + pagination
    │       ├── Upload.jsx           # CSV + Resume drag-and-drop
    │       └── Search.jsx           # Semantic search with section filters
    ├── vite.config.js               # Proxies /api → Django :8000
    └── package.json
```

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- A **MongoDB Atlas** account (free tier) → [cloud.mongodb.com](https://cloud.mongodb.com)
- A **Google AI Studio** API key (free) → [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/<your-username>/candidate-platform-django.git
cd candidate-platform-django
```

### Step 2 — Set up the Python backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

> ⚠️ **First run note:** `sentence-transformers` will download `all-MiniLM-L6-v2` (~80 MB) on first use. One-time only.

### Step 3 — Configure environment variables

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/
MONGODB_DB=candidate_platform
EMBEDDING_PROVIDER=sentence_transformers
ST_MODEL=all-MiniLM-L6-v2
DJANGO_SECRET_KEY=generate-a-real-secret-key
```

**Getting your MongoDB URI:**
1. [cloud.mongodb.com](https://cloud.mongodb.com) → Create free cluster
2. Click **Connect** → **Drivers** → copy the connection string
3. Replace `<password>` with your database user's password

**Getting your Gemini API key:**
1. [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → **Create API Key**

### Step 4 — Start the Django backend

```bash
# From backend/ with venv active
python manage.py runserver 8000
```

You should see:
```
System check identified no issues (0 silenced).
Starting development server at http://127.0.0.1:8000/
```

### Step 5 — Set up and start the React frontend

```bash
# In a new terminal, from the project root
cd frontend
npm install
npm run dev
```

Vite starts on **http://localhost:3000** and automatically proxies all `/api/*` calls to Django on port 8000.

### Step 6 — Open the app

| URL | Purpose |
|---|---|
| 👉 **http://localhost:3000** | React Dashboard |
| 📖 **http://localhost:8000/api/health** | API health check |

---

## 🔌 API Reference

All endpoints are prefixed with `/api/`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Server health check |
| `POST` | `/api/candidates/from-csv` | Upload recruiter CSV → ingest candidates |
| `POST` | `/api/candidates/from-resume` | Upload PDF/DOCX/TXT resume → ingest + enrich |
| `GET` | `/api/candidates` | List candidates (paginated: `?page=1&page_size=20`) |
| `GET` | `/api/candidates/search?q=` | Semantic similarity search |
| `GET` | `/api/candidates/<id>` | Get single candidate by ID |
| `GET` | `/api/candidates/<id>/confidence` | Per-field confidence breakdown |
| `POST` | `/api/candidates/<id>/enrich` | Trigger Gemini RAG enrichment |
| `POST` | `/api/candidates/merge` | Merge two candidate profiles |
| `DELETE` | `/api/candidates/<id>` | Delete a specific candidate |
| `DELETE` | `/api/candidates` | Clear all candidates |

---

## 💡 Usage Workflow

### 1. Upload a Recruiter CSV

Go to **Upload** page → drag & drop a `.csv` file.

The CSV can have varied column names — the parser handles all common formats:

```csv
name,email,phone,skills,title,location
Alice Johnson,alice@example.com,+14155550101,"Python,AWS,Docker",ML Engineer,San Francisco
Bob Smith,bob@example.com,+14155550202,"Java,Kubernetes",DevOps Lead,New York
```

### 2. Upload a Resume

Drop a **PDF**, **DOCX**, or **TXT** resume. The platform:
- Extracts raw text via LangChain loaders
- Matches to an existing candidate by email/phone (cross-upload deduplication)
- Runs Gemini structured extraction (skills, experience, education)
- Indexes resume chunks into MongoDB as vector embeddings

### 3. View Candidate Profiles

Click any candidate card to open the slide-out drawer with **three tabs**:

| Tab | Shows |
|---|---|
| **Profile** | AI summary, contact info, skills, experience, education |
| **Confidence** | Per-field confidence bars with source attribution |
| **Provenance** | Full audit trail of which source provided which field |

### 4. Enrich with Gemini

Click **✨ Enrich with Gemini** in the drawer footer:
1. Retrieves relevant chunks from MongoDB (RAG context)
2. Sends resume text + RAG context to Gemini 1.5 Flash
3. Gemini returns fully structured Pydantic JSON
4. Enriched data is merged back into the MongoDB candidate document

### 5. Semantic Search

Go to the **Search** page and type a natural language query:
```
Python developer with machine learning and AWS experience
Senior DevOps engineer with Kubernetes
```

---

## ⚙️ Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `GEMINI_MODEL` | ✅ | — | e.g. `gemini-1.5-flash` |
| `MONGODB_URI` | ✅ | — | Full MongoDB connection string |
| `MONGODB_DB` | No | `candidate_platform` | Database name |
| `EMBEDDING_PROVIDER` | No | `sentence_transformers` | `sentence_transformers` or `gemini` |
| `ST_MODEL` | No | `all-MiniLM-L6-v2` | HuggingFace model name |
| `DJANGO_SECRET_KEY` | ✅ (prod) | dev fallback | Django secret key |
| `DJANGO_DEBUG` | No | `True` | Set to `False` in production |
| `DJANGO_ALLOWED_HOSTS` | No | `*` | Comma-separated allowed hosts |

---

## 📄 License

MIT — use freely, attribution appreciated.

---

<p align="center">Built with ❤️ using Django · React · LangChain · MongoDB</p>
