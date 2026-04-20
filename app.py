from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
import uuid
import asyncio
import time
from pathlib import Path
from typing import Optional, List, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

import google.genai as genai
from google.genai import types as genai_types

# ─────────────────────────────────────────────────────────────
app = FastAPI(title="ResearchPal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# session_id → { vectorstore, history, filename, raw_text, pages, chunks }
SESSIONS: dict = {}

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Model priority — tries each in order on quota/503/404 errors
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-001",
    "gemini-flash-latest",
]

# ─────────────────────────────────────────────────────────────
# Embeddings — free, local CPU
# ─────────────────────────────────────────────────────────────
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

# ─────────────────────────────────────────────────────────────
# Gemini call — with model fallback + retry on 429 / 503
# ─────────────────────────────────────────────────────────────
def call_gemini(prompt: str, temperature: float = 0.2, max_tokens: int = 2048) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set. Create a .env file with your key.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    last_error = None

    for model in GEMINI_MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        candidate_count=1,
                    ),
                )
                return response.text  # ✓ success

            except Exception as e:
                last_error = e
                err = str(e)

                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    if "PerDay" in err or "limit: 0" in err:
                        print(f"[ResearchPal] Daily quota done for {model}, next model...")
                        break                           # skip to next model
                    wait = (2 ** attempt) * 12
                    print(f"[ResearchPal] Rate limited ({model}), wait {wait}s...")
                    time.sleep(wait)

                elif "503" in err or "UNAVAILABLE" in err or "high demand" in err.lower():
                    wait = (2 ** attempt) * 8
                    print(f"[ResearchPal] {model} overloaded, wait {wait}s...")
                    time.sleep(wait)

                elif "404" in err or "not found" in err.lower() or "MODEL_NOT_FOUND" in err:
                    print(f"[ResearchPal] {model} not available, next model...")
                    break                               # skip to next model

                else:
                    raise HTTPException(500, f"Gemini error: {err[:250]}")

    raise HTTPException(503,
        "Gemini is experiencing high demand. Please wait 30 seconds and try again.")


# ─────────────────────────────────────────────────────────────
# LangChain-compatible LLM wrapper (only used for retrieval)
# ─────────────────────────────────────────────────────────────
class GeminiLLM(LLM):
    temperature: float = 0.2
    max_tokens: int = 2048

    @property
    def _llm_type(self) -> str:
        return "gemini-direct"

    def _call(self, prompt: str,
              stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None,
              **kwargs: Any) -> str:
        return call_gemini(prompt, self.temperature, self.max_tokens)


# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

RAG_PROMPT_TEMPLATE = """You are ResearchPal — a world-class AI research assistant specializing in academic paper analysis. You have deep expertise in reading, interpreting, and explaining research papers across all scientific domains.

RETRIEVED CONTEXT FROM THE PAPER:
---
{context}
---

CONVERSATION HISTORY:
{chat_history}

STRICT RULES:
1. Answer ONLY using the context above. Never use outside knowledge.
2. If the answer is not present say: "This specific information is not in the retrieved sections. Try rephrasing or asking about a different aspect."
3. Always cite WHERE in the paper (e.g. "According to the methodology section..." or "The authors state in Section 4...").
4. For technical concepts: explain WHAT it is, then HOW the paper uses it.
5. Use bullet points or numbered lists for multi-part answers.
6. Quote numbers, metrics, equations exactly as they appear.
7. Match depth to question: concise for simple questions, thorough for complex ones.
8. Maintain context from conversation history for follow-up questions.

TONE: Expert but clear — like a senior researcher explaining to a peer.

CURRENT QUESTION: {question}

ANSWER (structured, accurate, evidence-based):"""

LR_EXTRACTION_PROMPT = """You are an elite academic literature analyst performing a systematic review extraction. Extract structured information from the research paper below.

PAPER CONTENT:
---
{paper_text}
---

EXTRACTION RULES:
- Be PRECISE — extract exactly what the paper states. Never invent.
- If a field cannot be found: write "Not explicitly stated in the paper."
- Methodology: 5-6 specific, sequential, action-oriented steps.
- limitations_llm: Be a critical peer reviewer — find gaps AUTHORS did NOT mention: dataset biases, scalability, evaluation weaknesses, reproducibility, generalizability, missing baselines.
- key_findings: Always include specific numbers/metrics where available.
- Return ONLY a valid JSON object. NO markdown fences. NO explanation. Start with {{ end with }}.

JSON TO RETURN:
{{
  "title": "Complete exact paper title",
  "authors": "Full names of all authors, comma-separated",
  "year": "4-digit publication year",
  "journal_conference": "Full name of journal or conference",
  "objective": "1-2 sentence precise statement of what the paper does and its scientific significance",
  "contributions": "3-5 numbered contributions, each a complete specific sentence. Format: 1. ... 2. ... 3. ...",
  "data_used": "All datasets/corpora with scale if mentioned (e.g. ImageNet: 1.2M images)",
  "model_used": "All models, algorithms, architectures, frameworks used",
  "methodology": [
    "Step 1 — Data Collection/Preparation: specific description",
    "Step 2 — Preprocessing/Feature Engineering: specific description",
    "Step 3 — Model Design/Architecture: specific description",
    "Step 4 — Training/Optimization: loss functions, optimizers, hyperparameters",
    "Step 5 — Evaluation/Validation: metrics, benchmarks, comparisons",
    "Step 6 — Analysis/Ablation: additional experiments or analysis"
  ],
  "key_findings": "3-5 most important results with specific numbers where available",
  "strengths": "3-4 specific strengths with justification",
  "limitations_self": "Limitations the AUTHORS explicitly acknowledged",
  "limitations_llm": "YOUR critical expert analysis: 3-5 gaps AUTHORS did NOT mention",
  "future_work": "Future directions authors suggested plus 2 extensions you identify"
}}"""


# ─────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str

class LRRequest(BaseModel):
    session_id: str


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def format_history(history: list) -> str:
    """Format chat history list into a clean string for the prompt."""
    if not history:
        return "No previous conversation."
    lines = []
    for turn in history[-6:]:   # last 6 turns = 12 messages max
        lines.append(f"User: {turn['user']}")
        lines.append(f"Assistant: {turn['assistant']}")
    return "\n".join(lines)

def retrieve_context(vectorstore, question: str, k: int = 6) -> tuple[str, list]:
    """MMR retrieval — diverse, non-redundant chunks."""
    docs = vectorstore.max_marginal_relevance_search(
        question, k=k, fetch_k=20, lambda_mult=0.7
    )
    context = "\n\n---\n\n".join(
        f"[Page {d.metadata.get('page', 0) + 1}]\n{d.page_content}" for d in docs
    )
    sources = []
    seen = set()
    for d in docs:
        page = d.metadata.get("page", 0)
        if page not in seen:
            seen.add(page)
            snippet = d.page_content[:200].replace("\n", " ").strip()
            sources.append({"page": page + 1, "snippet": snippet})
    return context, sources

def clean_text(raw: str, max_chars: int = 35000) -> str:
    text = re.sub(r'\n{3,}', '\n\n', raw)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text[:max_chars]


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=Path("static/index.html").read_text(encoding="utf-8"))


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not configured. Create a .env file.")

    session_id = str(uuid.uuid4())
    pdf_path = UPLOAD_DIR / f"{session_id}.pdf"
    pdf_path.write_bytes(await file.read())

    # Load PDF
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    if not pages:
        raise HTTPException(400, "Could not extract text. Use a text-based (not scanned) PDF.")

    raw_text = "\n".join(p.page_content for p in pages)

    # Chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    # Embed (local, free, CPU)
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Store session — NO LangChain chain, just the vectorstore + plain history list
    SESSIONS[session_id] = {
        "vectorstore": vectorstore,
        "history": [],             # list of {user, assistant} dicts
        "filename": file.filename,
        "raw_text": raw_text,
        "pages": len(pages),
        "chunks": len(chunks),
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "pages": len(pages),
        "chunks": len(chunks),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Session not found. Please upload a PDF first.")

    session = SESSIONS[req.session_id]
    vectorstore = session["vectorstore"]
    history = session["history"]

    # Step 1 — retrieve relevant chunks with MMR
    context, sources = await asyncio.to_thread(
        retrieve_context, vectorstore, req.message, 6
    )

    # Step 2 — build the prompt
    prompt = RAG_PROMPT_TEMPLATE.format(
        context=context,
        chat_history=format_history(history),
        question=req.message,
    )

    # Step 3 — call Gemini (with retry + model fallback built in)
    answer = await asyncio.to_thread(call_gemini, prompt, 0.2, 2048)

    # Step 4 — save to history
    history.append({"user": req.message, "assistant": answer})
    if len(history) > 20:          # keep max 20 turns to avoid memory bloat
        history.pop(0)

    return {"answer": answer, "sources": sources[:4]}


@app.post("/lr-table")
async def lr_table(req: LRRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(404, "Session not found.")

    session = SESSIONS[req.session_id]
    context = clean_text(session["raw_text"], max_chars=35000)
    prompt  = LR_EXTRACTION_PROMPT.format(paper_text=context)

    raw_str = await asyncio.to_thread(call_gemini, prompt, 0.1, 3000)

    try:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_str).strip()
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        match = re.search(r'\{[\s\S]+\}', cleaned)
        if not match:
            raise ValueError("No JSON object found in response")
        data = json.loads(match.group())
    except Exception as e:
        data = {
            "title": session["filename"].replace(".pdf", ""),
            "authors": "Click Generate LR Table again to retry",
            "year": "—", "journal_conference": "—",
            "objective": f"Parsing error: {str(e)[:120]}",
            "contributions": "—", "data_used": "—", "model_used": "—",
            "methodology": ["Extraction failed. Please click Generate LR Table again."],
            "key_findings": "—", "strengths": "—",
            "limitations_self": "—", "limitations_llm": "—", "future_work": "—",
        }

    return data


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "primary_model": GEMINI_MODELS[0],
        "fallback_models": GEMINI_MODELS[1:],
        "gemini_configured": bool(GEMINI_API_KEY),
        "active_sessions": len(SESSIONS),
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        pdf = UPLOAD_DIR / f"{session_id}.pdf"
        if pdf.exists():
            pdf.unlink()
    return {"status": "deleted"}
