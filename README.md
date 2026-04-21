<div align="center">

# 📄 ResearchPal

### AI-Powered Research Paper Assistant

*Upload any research paper and chat with it. Get instant answers, structured analysis, and exportable Literature Review tables — all for free.*

## What is ResearchPal?

ResearchPal is a web application that lets you upload any academic research paper (PDF) and interact with it through an AI-powered chatbot. Instead of reading through pages of dense academic text, you can simply ask questions and get precise, cited answers in seconds.

It also includes a **Literature Review Table generator** — click one button and get a fully structured extraction of the paper's key metadata, which you can export directly to Excel.

---

## Features

| Feature | Description |
|---|---|
| 📤 **PDF Upload** | Upload any research paper PDF |
| 💬 **AI Chat** | Ask anything about the paper with follow-up support |
| 📍 **Source Citations** | Every answer shows which page it came from |
| 📊 **LR Table Generator** | One-click structured metadata extraction |
| 📥 **Excel Export** | Download the LR table as a formatted `.xls` file |
| 🔒 **Session Isolated** | Each upload is independent and private |
| ⚡ **Fast** | Gemini 2.5 Flash responds in 2–4 seconds |
| 💸 **Free** | Zero cost — free Gemini API + free hosting |

---

## Literature Review Table Fields

When you click **Generate LR Table**, the app extracts all of these fields automatically:

| Field | Description |
|---|---|
| Paper Title | Exact title as it appears in the paper |
| Authors | All authors, full names |
| Year | Publication year |
| Journal / Conference | Venue name |
| Objective | What problem the paper solves and why it matters |
| Key Contributions | 4–5 numbered novel contributions |
| Data Used | All datasets with sample/patient counts |
| Model / Algorithm | All models, architectures, frameworks used |
| Methodology | 5-step sequential breakdown of the methods |
| Key Findings | Specific results with numbers and metrics |
| Strengths | What makes this paper valuable |
| Limitations (Authors) | What the authors themselves acknowledged |
| Limitations (LLM) | Additional gaps identified by AI peer review |
| Future Work | Suggested directions + reviewer recommendations |

---

## Tech Stack

```
Frontend     →  Vanilla HTML + CSS + JavaScript (single file, dark theme)
Backend      →  FastAPI (Python) — async, fast, production-grade
LLM          →  Google Gemini 2.5 Flash (free API, 1500 req/day)
Embeddings   →  sentence-transformers/all-MiniLM-L6-v2 (free, local CPU)
Vector DB    →  FAISS (in-memory, no external service needed)
PDF Parsing  →  PyPDF via LangChain document loaders
RAG          →  LangChain + MMR retrieval (diverse, non-redundant chunks)
Hosting      →  Hugging Face Spaces / Render.com (both free)
```

---

## How It Works

```
                    ┌─────────────────────────────────────┐
                    │           USER UPLOADS PDF           │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  PyPDF extracts text from all pages  │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  Text split into 1000-char chunks    │
                    │  with 150-char overlap               │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  all-MiniLM-L6-v2 embeds each chunk │
                    │  → stored in FAISS vector index      │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
   ┌──────────▼──────────┐               ┌─────────────▼──────────┐
   │    USER ASKS A      │               │  USER CLICKS LR TABLE   │
   │      QUESTION       │               │                         │
   └──────────┬──────────┘               └─────────────┬──────────┘
              │                                         │
   ┌──────────▼──────────┐               ┌─────────────▼──────────┐
   │  Question embedded  │               │  Call 1: Send first     │
   │  MMR search → top 6 │               │  3000 chars → extract   │
   │  relevant chunks    │               │  title, authors, year   │
   └──────────┬──────────┘               └─────────────┬──────────┘
              │                                         │
   ┌──────────▼──────────┐               ┌─────────────▼──────────┐
   │  Chunks + history   │               │  Call 2: Smart context  │
   │  injected into RAG  │               │  (methods/results/disc) │
   │  prompt → Gemini    │               │  → extract all content  │
   └──────────┬──────────┘               └─────────────┬──────────┘
              │                                         │
   ┌──────────▼──────────┐               ┌─────────────▼──────────┐
   │  Answer + page refs │               │  Merged LR Table JSON   │
   │  returned to user   │               │  → rendered + exportable│
   └─────────────────────┘               └────────────────────────┘
```

---

## Getting Started Locally

### Prerequisites
- Python 3.11+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/research-pal.git
cd research-pal
```

**2. Create a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your Gemini API key**

Create a file named `.env` in the project root:
```
GEMINI_API_KEY=your_api_key_here
```
Get your free key at: https://aistudio.google.com/app/apikey

**5. Run the app**
```bash
uvicorn app:app --reload --port 8000
```

**6. Open in browser**
```
http://localhost:8000
```

---

## Project Structure

```
research-pal/
├── app.py              # FastAPI backend — all routes and logic
├── requirements.txt    # Python dependencies
├── Procfile            # Deployment start command
├── Dockerfile          # For Hugging Face Spaces deployment
├── .gitignore          # Excludes .env, uploads/, venv/
└── static/
    └── index.html      # Complete frontend (HTML + CSS + JS)
```

---

## Deployment

### Option 1 — Hugging Face Spaces (Recommended, truly free)

1. Create account at [huggingface.co](https://huggingface.co)
2. New Space → Docker → Public
3. Push code: `git push hf main`
4. Add secret `GEMINI_API_KEY` in Space Settings
5. Live at: `https://huggingface.co/spaces/USERNAME/research-pal`

### Option 2 — Render.com (Free, no credit card)

1. Create account at [render.com](https://render.com) with GitHub
2. New Web Service → connect this repo
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add environment variable `GEMINI_API_KEY`
6. Deploy

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend |
| `POST` | `/upload` | Upload a PDF, returns session_id |
| `POST` | `/chat` | Send a question, get an answer |
| `POST` | `/lr-table` | Generate Literature Review table |
| `GET` | `/health` | Check app status and config |
| `DELETE` | `/session/{id}` | Clean up a session |

---

## Concepts Used

This project applies the following concepts from AI agent development:

**RAG (Retrieval Augmented Generation)** — Instead of sending the entire paper to the LLM every time (expensive, slow), the paper is chunked, embedded, and stored in a vector database. At query time only the most relevant chunks are retrieved and sent to the LLM. This grounds the LLM's answers in the actual paper content.

**Embeddings** — Each text chunk is converted to a 384-dimensional vector using `sentence-transformers/all-MiniLM-L6-v2`. Vectors that are semantically similar are close together in vector space, enabling meaning-based search rather than keyword matching.

**FAISS Vector Store** — Facebook's fast similarity search library stores all chunk embeddings in memory and finds the most similar vectors to a query in milliseconds using approximate nearest neighbor search.

**MMR (Maximum Marginal Relevance)** — When retrieving chunks, MMR selects chunks that are both relevant to the query AND diverse from each other. This prevents retrieving 6 nearly identical chunks from the same paragraph.

**Prompt Engineering** — The system uses carefully structured prompts with explicit rules, section guidance, and output format constraints. The LR table uses two separate focused prompts (one for metadata, one for content) rather than one large prompt, which dramatically improves accuracy.

**Conversation Memory** — Chat history is stored as a plain Python list of `{user, assistant}` dictionaries per session, formatted into the prompt as context. This enables natural follow-up questions without re-uploading the paper.

**Model Fallback with Retry** — The Gemini API call includes automatic fallback across multiple models (`gemini-2.5-flash` → `gemini-2.0-flash-lite` → `gemini-flash-latest`) with exponential backoff retry on rate limits (429) and overload errors (503).

**Async Architecture** — FastAPI runs on asyncio. Blocking operations (PDF parsing, embedding, Gemini API calls) are offloaded to thread pools with `asyncio.to_thread()` so the server never blocks while waiting for responses.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Your Google Gemini API key |

---

## Free Tier Limits

| Service | Free Limit |
|---|---|
| Gemini API | 1,500 requests/day, 15 RPM |
| Hugging Face Spaces | Unlimited (CPU basic) |
| Render.com | 750 hours/month |
| FAISS | No limit (in-memory) |
| sentence-transformers | No limit (runs locally) |

---

## Contributing

Pull requests are welcome. For major changes please open an issue first.

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">
Built with FastAPI · LangChain · Google Gemini · FAISS · sentence-transformers
</div>
