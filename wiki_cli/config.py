"""Paths and settings for the Romans study wiki harness. Everything here is local."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VAULT = ROOT / "vault"             # the Obsidian vault (human-facing)
RAW_DIR = VAULT / "raw"            # unchanged original sources
WIKI_DIR = VAULT / "wiki"          # Gemma-generated, human-reviewed notes
INDEX_MD = VAULT / "index.md"      # human landing page
CATALOG_MD = VAULT / "Source Catalog.md"

DATA = ROOT / "data"               # machine files, kept OUTSIDE the vault
MANIFEST = DATA / "manifest.json"  # source id -> hash, pages it produced
PAGES = DATA / "pages.json"        # structured page content the wiki is rendered from
SEARCH_INDEX = DATA / "search_index.json"
LOG_DIR = DATA / "logs"

PROMPTS = ROOT / "prompts"
PERSONA = PROMPTS / "persona.md"
RESEARCH_RULES = PROMPTS / "wiki-instructions.md"

EVIDENCE = ROOT / "evidence"

# Local model served by Ollama on this machine.
OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma4:e2b-it-qat"        # Gemma 4 E2B, instruction-tuned, Q4_0 (QAT)
NUM_CTX = 8192                     # context window we request from Ollama
REQUEST_TIMEOUT = 600              # seconds; first call includes model load

# Retrieval
PASSAGE_MAX_WORDS = 120            # split sections larger than this at child bullets
TOP_K = 5                          # passages handed to Gemma in ask/chat (was 4; see evidence/retrieval-tuning.md)
# Chat looks up notes when the message names the study (Romans, a verse, "notes") or when at
# least half its content words occur in the notes and the best BM25 score clears a floor.
CHAT_STUDY_WORDS = r"\b(romans?|chapter|verses?|notes?|study|bible|scripture)\b|\b\d+:\d+"
CHAT_MIN_VOCAB_OVERLAP = 0.5
CHAT_MIN_SCORE = 1.5

# Chat
CHAT_HISTORY_TURNS = 6             # user+assistant pairs kept as conversation context
