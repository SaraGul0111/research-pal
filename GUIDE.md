# ResearchPal — Complete Setup & Deployment Guide
# ================================================
# PDF Research Assistant with LR Table Generator
# Zero cost · CPU friendly · Free deployment
# ================================================

## WHAT YOU ARE BUILDING
A web chatbot where users upload research PDFs, chat with them,
and generate structured Literature Review tables — all for free.

## TECHNOLOGY STACK
- Backend  : FastAPI (Python)
- LLM      : Ollama (runs locally on your machine, FREE)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (FREE, runs on CPU)
- Vector DB : FAISS (in-memory, no server needed)
- Frontend  : Vanilla HTML/CSS/JS (single file)
- Deployment: Railway.app (FREE tier, public URL)

────────────────────────────────────────────────────────────────
## STEP 1 — INSTALL PYTHON
────────────────────────────────────────────────────────────────
1. Go to https://python.org/downloads
2. Download Python 3.11 (recommended) — NOT 3.13
3. Install it — CHECK "Add Python to PATH" during install
4. Verify: open terminal/CMD and type:
   python --version
   → Should show: Python 3.11.x

────────────────────────────────────────────────────────────────
## STEP 2 — INSTALL OLLAMA (FREE LOCAL LLM)
────────────────────────────────────────────────────────────────
Ollama runs LLMs (like Llama 3.2) locally on your computer.
No API key, no cost, no internet needed for inference.

1. Go to https://ollama.com/download
2. Download for your OS (Windows / Mac / Linux)
3. Install it (just run the installer)
4. Open a NEW terminal and run:
   ollama pull llama3.2
   → This downloads the Llama 3.2 model (~2GB, one-time download)
   → Wait until it says "success"

5. Optional — if you have 8GB+ RAM and want a smarter model:
   ollama pull mistral
   Then change "llama3.2" to "mistral" in app.py line 48

6. Test Ollama is working:
   ollama run llama3.2 "What is machine learning?"
   → Should get a response. Press CTRL+C to exit.

────────────────────────────────────────────────────────────────
## STEP 3 — SET UP YOUR PROJECT FOLDER
────────────────────────────────────────────────────────────────
Your project should have this structure:

  research-pal/
  ├── app.py              ← FastAPI backend
  ├── requirements.txt    ← Python packages
  ├── Procfile            ← For deployment
  ├── .gitignore          ← Files to exclude from git
  └── static/
      └── index.html      ← Frontend (UI)

1. Create the folder somewhere you work:
   mkdir research-pal
   cd research-pal
   mkdir static

2. Place all the files Claude gave you in the correct locations.

────────────────────────────────────────────────────────────────
## STEP 4 — CREATE VIRTUAL ENVIRONMENT & INSTALL PACKAGES
────────────────────────────────────────────────────────────────
Inside your research-pal folder, run these commands one by one:

Windows:
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt

Mac/Linux:
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt

→ This installs FastAPI, LangChain, FAISS, sentence-transformers etc.
→ Takes 3-5 minutes (downloads ~1GB of packages)
→ You will see (venv) in your terminal prompt when activated

────────────────────────────────────────────────────────────────
## STEP 5 — START OLLAMA IN THE BACKGROUND
────────────────────────────────────────────────────────────────
Open a SEPARATE terminal window and run:
  ollama serve

→ Keep this terminal open always while testing
→ It will say "Listening on 127.0.0.1:11434"
→ This is the local LLM server your backend talks to

────────────────────────────────────────────────────────────────
## STEP 6 — RUN THE APP LOCALLY
────────────────────────────────────────────────────────────────
In your original terminal (with venv activated):
  uvicorn app:app --reload --port 8000

→ You should see:
  INFO:     Uvicorn running on http://127.0.0.1:8000

Open your browser and go to:
  http://localhost:8000

→ You should see the ResearchPal interface!

TEST IT:
1. Click the upload zone or drag a PDF
2. Wait for "Paper indexed successfully!" toast
3. Ask: "What is the main objective of this paper?"
4. Click "Generate LR Table" in the sidebar
5. Wait 30-60 seconds for the table to appear
6. Try exporting as CSV or JSON

────────────────────────────────────────────────────────────────
## STEP 7 — DEPLOY TO RAILWAY (FREE PUBLIC URL)
────────────────────────────────────────────────────────────────
Railway gives you a free public URL so anyone can access your app.

IMPORTANT NOTE ABOUT OLLAMA ON RAILWAY:
Railway doesn't have Ollama installed. For deployment, you have
two options:

OPTION A (Recommended — add Groq API, still FREE):
  Groq offers a FREE API for Llama 3. 8K requests/day free.
  See "OPTION A" section below.

OPTION B (Keep Ollama, only works locally):
  If you only want local use, skip deployment and just share
  your localhost with ngrok (see OPTION B section).

── OPTION A: Deploy with Groq (Free API) ──────────────────────

1. Go to https://console.groq.com
2. Sign up (free)
3. Go to "API Keys" → Create key → Copy it

4. Modify app.py — replace the get_llm() function:

   REPLACE THIS in app.py:
   ┌────────────────────────────────────────────────────────────┐
   │ from langchain_community.llms import Ollama               │
   │                                                            │
   │ def get_llm():                                             │
   │     return Ollama(                                         │
   │         model="llama3.2",                                  │
   │         temperature=0.1,                                   │
   │         num_ctx=4096,                                      │
   │     )                                                      │
   └────────────────────────────────────────────────────────────┘

   WITH THIS:
   ┌────────────────────────────────────────────────────────────┐
   │ from langchain_groq import ChatGroq                        │
   │ import os                                                  │
   │                                                            │
   │ def get_llm():                                             │
   │     return ChatGroq(                                       │
   │         model="llama-3.1-8b-instant",                      │
   │         api_key=os.environ["GROQ_API_KEY"],                │
   │         temperature=0.1,                                   │
   │     )                                                      │
   └────────────────────────────────────────────────────────────┘

5. Add to requirements.txt:
   langchain-groq==0.2.1

6. For local testing with Groq, create a .env file:
   GROQ_API_KEY=your_groq_api_key_here

   And add to top of app.py:
   from dotenv import load_dotenv
   load_dotenv()

   Add to requirements.txt:
   python-dotenv==1.0.1

── OPTION B: Share locally with ngrok (No changes needed) ──────

1. Go to https://ngrok.com → Sign up (free)
2. Download ngrok for your OS
3. Run your app: uvicorn app:app --reload --port 8000
4. In another terminal: ngrok http 8000
5. You get a URL like: https://abc123.ngrok-free.app
6. Share this URL — it works as long as your computer is on

── DEPLOY TO RAILWAY (for Option A) ───────────────────────────

STEP A: Push to GitHub
1. Go to https://github.com → Sign in → New repository
2. Name it "research-pal" → Create
3. In your project folder:
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/research-pal.git
   git push -u origin main

STEP B: Deploy on Railway
1. Go to https://railway.app → Sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select "research-pal"
4. Railway detects Python automatically
5. Go to "Variables" tab → Add:
   GROQ_API_KEY = your_groq_api_key_here
6. Go to "Settings" → "Networking" → "Generate Domain"
7. Your app is live at: https://research-pal-xxx.railway.app

STEP C: Watch the deployment
- Click "Deployments" tab to see build logs
- First deploy takes 3-5 minutes (installs packages)
- Subsequent deploys are faster
- If build fails, check logs for errors

────────────────────────────────────────────────────────────────
## TROUBLESHOOTING
────────────────────────────────────────────────────────────────

Problem: "ollama: command not found"
Fix: Restart terminal after installing Ollama, or add to PATH

Problem: "Connection refused" when uploading PDF
Fix: Make sure "ollama serve" is running in separate terminal

Problem: LR Table times out
Fix: Llama 3.2 is smaller/faster. If using mistral and it's slow,
     switch back to llama3.2 in app.py line 48

Problem: "No module named 'langchain'"
Fix: Make sure you activated venv first:
     Windows: venv\Scripts\activate
     Mac/Linux: source venv/bin/activate

Problem: Port 8000 already in use
Fix: Use a different port:
     uvicorn app:app --reload --port 8001
     Then go to http://localhost:8001

Problem: PDF not loading / 0 chunks
Fix: Some PDFs are scanned images. Try a text-based PDF.
     Test with any arXiv paper (https://arxiv.org)

Problem: Railway build fails
Fix: Check requirements.txt has exact versions. Make sure
     Procfile exists with correct content.

────────────────────────────────────────────────────────────────
## HOW THE APP WORKS (Technical Summary)
────────────────────────────────────────────────────────────────

1. USER UPLOADS PDF
   → PyPDF loads and extracts text
   → RecursiveCharacterTextSplitter chunks it (800 chars, 100 overlap)
   → all-MiniLM-L6-v2 embeds each chunk (FREE, runs on CPU)
   → FAISS stores all vectors in memory
   → ConversationalRetrievalChain is created with this vectorstore

2. USER ASKS QUESTION
   → Question is embedded using the same model
   → FAISS finds top 5 most similar chunks (cosine similarity)
   → Chunks are injected into the RAG prompt
   → Ollama/Groq generates answer grounded in those chunks
   → Last 8 messages kept in memory for follow-up questions
   → Source page numbers returned with the answer

3. LR TABLE GENERATION
   → First 6000 + last 2000 characters of paper sent to LLM
   → LLM asked to extract all 14 fields as JSON
   → JSON parsed and rendered as a beautiful card grid
   → Export as CSV or JSON available

────────────────────────────────────────────────────────────────
## UPGRADING / CUSTOMIZING
────────────────────────────────────────────────────────────────

Change the LLM model (Ollama):
  Edit app.py line 48: model="mistral"  # or "llama3.1", "phi3"
  Run: ollama pull mistral

Add more document types (Word, web pages):
  from langchain_community.document_loaders import Docx2txtLoader
  from langchain_community.document_loaders import WebBaseLoader

Persist the vector store (survive restarts):
  vectorstore.save_local("faiss_index")
  # Load with: FAISS.load_local("faiss_index", embeddings)

Change chunk size (for better accuracy):
  Edit app.py: chunk_size=1024, chunk_overlap=150

────────────────────────────────────────────────────────────────
## QUICK COMMAND REFERENCE
────────────────────────────────────────────────────────────────

# Activate virtual environment
Windows:    venv\Scripts\activate
Mac/Linux:  source venv/bin/activate

# Install packages
pip install -r requirements.txt

# Pull Ollama model
ollama pull llama3.2

# Start Ollama (separate terminal, keep running)
ollama serve

# Run the app
uvicorn app:app --reload --port 8000

# View at
http://localhost:8000

# Deploy update to Railway
git add .
git commit -m "update"
git push origin main
# Railway auto-deploys on push
