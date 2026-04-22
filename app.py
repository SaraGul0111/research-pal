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
print("[ResearchPal] Loading embedding model...")
EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
print("[ResearchPal] Embedding model ready.")

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
2. If the answer seems absent, look harder — limitations are often in the Discussion section, the last paragraphs, or phrased as "future work", "constraints", "our study has", "one limitation", "we acknowledge". Check every part of the context before saying it is not found.
3. Only if truly absent say: "This specific information is not in the retrieved sections. Try asking: what does the discussion section say?"
4. Always cite WHERE in the paper (e.g. "According to the methodology section..." or "The authors state in Section 4...").
5. For technical concepts: explain WHAT it is, then HOW the paper uses it.
6. Use bullet points or numbered lists for multi-part answers.
7. Quote numbers, metrics, equations exactly as they appear.
8. Match depth to question: concise for simple questions, thorough for complex ones.
9. Maintain context from conversation history for follow-up questions.
TONE: Expert but clear — like a senior researcher explaining to a peer.
CURRENT QUESTION: {question}

IMPORTANT — If the question is about limitations, future work, conclusion, or discussion:
These are always in the LAST section of the paper. Look for phrases like "our study has", "we acknowledge", "one limitation", "future studies should", "further research", "in conclusion", "to summarize". Check every part of the retrieved context carefully including the last pages section if provided.
ANSWER (structured, accurate, evidence-based):"""


# ── Prompt 1: Basic metadata — title authors year journal ──────
LR_PROMPT_BASIC = """Read the research paper below very carefully.
Your job: extract ONLY the basic bibliographic information.
Return ONLY a raw JSON object — no markdown, no code fences, no explanation.
Start with {{ and end with }}.
PAPER TEXT (first section):
{paper_text}
Extract these fields exactly as they appear in the paper:
{{
  "title": "Copy the EXACT title word-for-word from the paper header or title page. Do not paraphrase or shorten it.",
  "authors": "Copy ALL author names exactly as listed in the paper, comma separated. Include every author.",
  "year": "The 4-digit publication year",
  "journal_conference": "The exact journal or conference name where this was published"
}}"""

# ── Prompt 2: Deep content — everything else ──────────────────
LR_PROMPT_CONTENT = """You are a senior academic peer reviewer. Read this research paper carefully.
Return ONLY a raw JSON object — no markdown, no code fences, no explanation.
Start with {{ and end with }}.
CRITICAL: Every single field below MUST have real content from the paper.
Never write "Not found" — dig deeper into the text to find each answer.
PAPER TEXT:
{paper_text}
Instructions per field:
- objective: Read the abstract and introduction. What problem does this paper solve? What is the proposed method? Why does it matter? Write 2-3 sentences.
- contributions: Read the introduction (usually a bulleted list "In this paper we...") and conclusion. List 4-5 numbered contributions.
- data_used: Read the Methods/Data section. List every dataset name with patient/sample counts.
- model_used: Read Methods carefully. List every model, architecture, algorithm mentioned: CNN, transformer, ResNet, MIL, attention, optimizer names, frameworks (PyTorch etc).
- methodology: Read the entire Methods section. Write exactly 5 sequential steps describing what the researchers DID.
- key_findings: Read Results AND Discussion sections. Find AUC values, accuracy numbers, p-values, comparison to baselines, number of cases. Write 4-5 specific findings with exact numbers.
- strengths: What makes this paper good? Think: dataset size, multi-center, clinical validation, novelty, reproducibility. Write 3-4 specific strengths.
- limitations_self: Read the Limitations section or end of Discussion. What do the AUTHORS say are their own limitations? Quote or closely paraphrase.
- limitations_llm: As a critical reviewer, what weaknesses did authors NOT mention? Think: external validation, class imbalance, black-box interpretability, prospective study missing, computational cost, specific demographic biases. Write 4-5 you identify.
- future_work: Read the last paragraphs. What future directions do authors suggest? Add 2 more you think are logical.
Return this JSON with ALL fields filled with real content:
{{
  "objective": "2-3 sentences describing the problem, proposed solution, and clinical significance",
  "contributions": "1. first contribution sentence. 2. second. 3. third. 4. fourth. 5. fifth if exists.",
  "data_used": "all datasets with patient and sample counts",
  "model_used": "every model architecture algorithm framework mentioned in the paper",
  "methodology": [
    "Step 1 — [name]: specific description of what was done",
    "Step 2 — [name]: specific description",
    "Step 3 — [name]: specific description",
    "Step 4 — [name]: specific description",
    "Step 5 — [name]: specific description"
  ],
  "key_findings": "4-5 specific results with exact numbers from the paper: AUC values, accuracy, number of cases identified, comparison improvements",
  "strengths": "3-4 specific strengths with justification from this specific paper",
  "limitations_self": "exact limitations the authors stated in their own words",
  "limitations_llm": "1. limitation one. 2. limitation two. 3. limitation three. 4. limitation four. — limitations authors did NOT mention",
  "future_work": "what authors suggest for future work, plus 2 additional directions you recommend"
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
    for turn in history[-5:]:   # last 5 turns = 10 messages max
        lines.append(f"User: {turn['user']}")
        lines.append(f"Assistant: {turn['assistant']}")
    return "\n".join(lines)

def retrieve_context(vectorstore, question: str, k: int = 6) -> tuple[str, list]:
    """MMR retrieval — diverse, non-redundant chunks."""
    docs = vectorstore.max_marginal_relevance_search(
        question, k=k, fetch_k=30, lambda_mult=0.7
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

def smart_paper_context(raw_text: str, max_chars: int = 40000) -> str:
    """
    Send the full paper text to Gemini.
    If paper is very long, prioritize: abstract + intro + methods + results + discussion + conclusion.
    This ensures key sections are always included even if paper is truncated.
    """
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    if len(text) <= max_chars:
        return text  # short paper — send everything

    # Long paper — find key sections and prioritize them
    text_lower = text.lower()
    sections = {}
    section_keywords = [
        ('abstract', ['abstract']),
        ('introduction', ['introduction', 'background']),
        ('methods', ['method', 'material', 'approach', 'experiment']),
        ('results', ['result', 'finding']),
        ('discussion', ['discussion']),
        ('conclusion', ['conclusion', 'summary']),
        ('limitation', ['limitation']),
    ]
    for section_name, keywords in section_keywords:
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                sections[section_name] = idx
                break

    if not sections:
        # No sections found — just send first + last portions
        half = max_chars // 2
        return text[:half] + "\n\n[... middle section truncated ...]\n\n" + text[-half:]

    # Build context by stitching important sections
    sorted_sections = sorted(sections.items(), key=lambda x: x[1])
    result_parts = []
    chars_used = 0
    budget = max_chars

    for i, (name, start) in enumerate(sorted_sections):
        # End of this section = start of next section (or end of text)
        end = sorted_sections[i+1][1] if i+1 < len(sorted_sections) else len(text)
        section_text = text[start:end].strip()

        # Give more budget to methods, results, discussion
        if name in ('methods', 'results', 'discussion', 'limitation'):
            allowed = min(len(section_text), budget // 2)
        else:
            allowed = min(len(section_text), budget // 4)

        if chars_used + allowed > budget:
            allowed = budget - chars_used

        if allowed > 100:
            result_parts.append(f"[{name.upper()}]\n" + section_text[:allowed])
            chars_used += allowed

        if chars_used >= budget:
            break

    return "\n\n".join(result_parts)


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
    vectorstore = await asyncio.to_thread(
    FAISS.from_documents, chunks, EMBEDDINGS)

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

    session  = SESSIONS[req.session_id]
    raw_text = session["raw_text"]

    # Call 1 — basic metadata from first 3000 chars (title/authors always at top)
    first_section = clean_text(raw_text[:8000], max_chars=8000)
    prompt_basic  = LR_PROMPT_BASIC.format(paper_text=first_section)
    raw_basic     = await asyncio.to_thread(call_gemini, prompt_basic, 0.0, 2048)
    basic_data    = parse_lr_response(raw_basic, session["filename"])

    # Call 2 — deep content from smart context (methods/results/discussion)
    full_context    = smart_paper_context(raw_text, max_chars=40000)
    prompt_content  = LR_PROMPT_CONTENT.format(paper_text=full_context)
    raw_content     = await asyncio.to_thread(call_gemini, prompt_content, 0.0, 4096)
    content_data    = parse_lr_response(raw_content, session["filename"])

    # Merge: basic_data provides title/authors/year/journal
    #        content_data provides everything else
    merged = {
        "title":              basic_data.get("title", session["filename"].replace(".pdf","")),
        "authors":            basic_data.get("authors", "See paper"),
        "year":               basic_data.get("year", "—"),
        "journal_conference": basic_data.get("journal_conference", "—"),
        "objective":          content_data.get("objective", "—"),
        "contributions":      content_data.get("contributions", "—"),
        "data_used":          content_data.get("data_used", "—"),
        "model_used":         content_data.get("model_used", "—"),
        "methodology":        content_data.get("methodology", ["—"]),
        "key_findings":       content_data.get("key_findings", "—"),
        "strengths":          content_data.get("strengths", "—"),
        "limitations_self":   content_data.get("limitations_self", "—"),
        "limitations_llm":    content_data.get("limitations_llm", "—"),
        "future_work":        content_data.get("future_work", "—"),
    }
    return merged


def parse_lr_response(raw_str: str, filename: str) -> dict:
    """
    Robust JSON parser — handles all the ways Gemini might format its response:
    - Pure JSON
    - JSON wrapped in ```json ... ```
    - JSON wrapped in ``` ... ```
    - JSON with explanation text before/after
    - Slightly malformed JSON
    """
    if not raw_str:
        return fallback_lr(filename, "Empty response from Gemini")

    # Step 1 — strip markdown code fences (most common issue)
    cleaned = raw_str.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$",          "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Step 2 — try direct parse first
    try:
        data = json.loads(cleaned)
        return ensure_all_fields(data, filename)
    except json.JSONDecodeError:
        pass

    # Step 3 — find the outermost { ... } block
    try:
        start = cleaned.index("{")
        # find matching closing brace
        depth = 0
        end   = start
        for i, ch in enumerate(cleaned[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        json_str = cleaned[start:end + 1]
        data = json.loads(json_str)
        return ensure_all_fields(data, filename)
    except (ValueError, json.JSONDecodeError):
        pass

    # Step 4 — fix common issues: trailing commas, single quotes
    try:
        fixed = re.sub(r",\s*([}\]])", r"", cleaned)   # trailing commas
        fixed = re.sub(r"'([^']*)'", r'""', fixed)      # single → double quotes
        start = fixed.index("{")
        data  = json.loads(fixed[start:])
        return ensure_all_fields(data, filename)
    except Exception:
        pass

    # Step 5 — extract field by field using regex (last resort)
    data = extract_fields_by_regex(cleaned, filename)
    return data


def ensure_all_fields(data: dict, filename: str) -> dict:
    """Make sure all required fields exist with fallback values."""
    required = {
        "title":              filename.replace(".pdf", ""),
        "authors":            "Not found in paper",
        "year":               "—",
        "journal_conference": "Not found in paper",
        "objective":          "Not found in paper",
        "contributions":      "Not found in paper",
        "data_used":          "Not found in paper",
        "model_used":         "Not found in paper",
        "methodology":        ["Could not extract methodology steps"],
        "key_findings":       "Not found in paper",
        "strengths":          "Not found in paper",
        "limitations_self":   "Not found in paper",
        "limitations_llm":    "Not found in paper",
        "future_work":        "Not found in paper",
    }
    for key, default in required.items():
        if key not in data or not data[key] or data[key] == "":
            data[key] = default
    # Ensure methodology is always a list
    if isinstance(data["methodology"], str):
        steps = re.split(r"(?:Step\s*\d+[:\-–]|\d+[.\)]\s*)", data["methodology"])
        data["methodology"] = [s.strip() for s in steps if s.strip()]
        if not data["methodology"]:
            data["methodology"] = [data["methodology"] if isinstance(data["methodology"], str) else "See paper"]
    return data


def extract_fields_by_regex(text: str, filename: str) -> dict:
    """Extract individual fields using regex when full JSON parsing fails."""
    def get_field(pattern):
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else "Not found in paper"

    # Try to extract title, authors, year from the text
    title   = get_field(r'"title"\s*:\s*"([^"]+)"')
    authors = get_field(r'"authors"\s*:\s*"([^"]+)"')
    year    = get_field(r'"year"\s*:\s*"([^"]+)"')
    journal = get_field(r'"journal_conference"\s*:\s*"([^"]+)"')
    obj     = get_field(r'"objective"\s*:\s*"([^"]+)"')
    contrib = get_field(r'"contributions"\s*:\s*"([^"]+)"')
    data_u  = get_field(r'"data_used"\s*:\s*"([^"]+)"')
    model_u = get_field(r'"model_used"\s*:\s*"([^"]+)"')
    findings= get_field(r'"key_findings"\s*:\s*"([^"]+)"')
    strengths=get_field(r'"strengths"\s*:\s*"([^"]+)"')
    lim_s   = get_field(r'"limitations_self"\s*:\s*"([^"]+)"')
    lim_l   = get_field(r'"limitations_llm"\s*:\s*"([^"]+)"')
    future  = get_field(r'"future_work"\s*:\s*"([^"]+)"')

    # Extract methodology array
    method_match = re.search(r'"methodology"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if method_match:
        steps_raw = method_match.group(1)
        steps = re.findall(r'"([^"]+)"', steps_raw)
        methodology = steps if steps else ["Could not extract steps"]
    else:
        methodology = ["Could not extract methodology steps"]

    return {
        "title": title if title != "Not found in paper" else filename.replace(".pdf",""),
        "authors": authors, "year": year,
        "journal_conference": journal, "objective": obj,
        "contributions": contrib, "data_used": data_u,
        "model_used": model_u, "methodology": methodology,
        "key_findings": findings, "strengths": strengths,
        "limitations_self": lim_s, "limitations_llm": lim_l,
        "future_work": future,
    }


def fallback_lr(filename: str, reason: str) -> dict:
    return {
        "title": filename.replace(".pdf", ""),
        "authors": "Click Generate LR Table again",
        "year": "—", "journal_conference": "—",
        "objective": f"Extraction failed: {reason}. Please click Generate LR Table again.",
        "contributions": "—", "data_used": "—", "model_used": "—",
        "methodology": ["Please click Generate LR Table again."],
        "key_findings": "—", "strengths": "—",
        "limitations_self": "—", "limitations_llm": "—", "future_work": "—",
    }


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
