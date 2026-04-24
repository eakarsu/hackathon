#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lowes RAG + Action Items app (CLI)
----------------------------------
- Index a CSV and a rules file into a Chroma vector DB
- Retrieve the most relevant chunks
- Call Lowes B2B /v1/chat/completions with model `chatgpt_4o`
- Produce exactly five actionable items based on the rules (+ optional CSV context)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import functools
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

# ---------- Chroma & embeddings ----------
try:
    import chromadb
    from chromadb.utils import embedding_functions as cef
except Exception as e:
    print("ERROR: chromadb not available. Install dependencies with:")
    print("  pip install -r requirements.txt")
    raise

# ---------- Logging ----------
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("lowes_rag_app")

# ---- DANGEROUS: disables TLS verification in this process ----
import os, ssl, warnings

# Remove CA bundle env vars so they don't interfere with verify=False
for var in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE"):
    os.environ.pop(var, None)

# If you rely on HF Hub offline/cached models, keep these if you like:
os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFICATION", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Disable urllib3/requests warnings and verification
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter("ignore", InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Patch requests to default to verify=False
import requests
_old_request = requests.Session.request
def _request(self, method, url, **kwargs):
    kwargs.setdefault("verify", False)
    return _old_request(self, method, url, **kwargs)
requests.Session.request = _request

# If any lib uses httpx, disable there too
try:
    import httpx
    _old_httpx_init = httpx.Client.__init__
    def _httpx_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        return _old_httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = _httpx_init
except Exception:
    pass

print("WARNING: SSL certificate verification DISABLED for this process")
# ---- end dangerous block ----

# =======================================
# Auth + Chat Client for Lowes B2B API
# =======================================

class LowesAuthClient:
    """Simple OAuth2 Client Credentials helper for Lowes B2B."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str = "https://apis-b2b-stage.lowes.com/v1/oauthprovider/oauth2/token",
        timeout: int = 20,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.timeout = timeout
        self._token: Optional[str] = None
        self._expiry: float = 0.0
        self._session = requests.Session()

    def get_token(self) -> str:
        now = time.time()
        # Refresh 30s before expiry
        if self._token and now < (self._expiry - 30):
            return self._token

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        resp = self._session.post(self.token_url, headers=headers, data=data, timeout=self.timeout)
        if resp.status_code != 200:
            msg = f"Failed to obtain token: HTTP {resp.status_code} - {resp.text}"
            raise RuntimeError(msg)
        body = resp.json()
        if "access_token" not in body:
            raise RuntimeError(f"Token response missing access_token: {body}")
        self._token = body["access_token"]
        expires_in = int(body.get("expires_in", 900))
        self._expiry = now + expires_in
        logger.info("Obtained OAuth2 token (expires in %ss)", expires_in)
        return self._token

    def close(self):
        """Close the session"""
        if hasattr(self, '_session') and self._session:
            self._session.close()


class LowesAIClient:
    """Chat client to call /v1/chat/completions with model `chatgpt_4o` (default)."""

    def __init__(
        self,
        auth: LowesAuthClient,
        chat_url: str = "https://apis-b2b-stage.lowes.com/v1/chat/completions",
        model: str = "chatgpt_4o",
        timeout: int = 60,
    ) -> None:
        self.auth = auth
        self.chat_url = chat_url
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token = self.auth.get_token()
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if extra_params:
            payload.update(extra_params)

        resp = self._session.post(self.chat_url, headers=headers, json=payload, timeout=self.timeout)
        try:
            data = resp.json()
        except Exception:
            data = {"error": {"message": f"Non-JSON response: {resp.text}", "http_status": resp.status_code}}

        # Surface HTTP & API errors coherently
        if resp.status_code >= 400 or "error" in data:
            # Pass through API-provided error if present
            if "error" in data:
                err = data["error"]
            else:
                err = {"message": f"HTTP {resp.status_code}: {resp.text}"}
            raise RuntimeError(f"Chat API error: {json.dumps(err, ensure_ascii=False)}")

        return data

    @staticmethod
    def extract_text(response_json: Dict[str, Any]) -> str:
        """Extract assistant text safely from a Chat Completions-like response."""
        # Try OpenAI-style
        try:
            return response_json["choices"][0]["message"]["content"]
        except Exception:
            # Fallback: return the whole payload
            return json.dumps(response_json, ensure_ascii=False)

    def close(self):
        """Close the session"""
        if hasattr(self, '_session') and self._session:
            self._session.close()


# =======================================
# Embeddings + Vector store (Chroma)
# =======================================

def build_chroma_collection(persist_dir: str, collection_name: str = 'leads_kb'):
    """Build Chroma collection with local model and correct interface"""
    import re
    if not (3 <= len(collection_name) <= 63):
        raise ValueError(f"Collection name must be 3-63 characters, got '{collection_name}' ({len(collection_name)} chars)")
    
    pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9_-]{1,61}[a-zA-Z0-9])?$"
    if not re.match(pattern, collection_name):
        raise ValueError(f"Invalid collection name '{collection_name}'")

    try:
        client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"Using persistent Chroma client at {persist_dir}")
    except Exception as e:
        logger.warning(f"Falling back to in-memory Chroma client: {e}")
        client = chromadb.Client()

    try:
        from sentence_transformers import SentenceTransformer
        
        class FixedEmbeddingFunction:
            def __init__(self, model_path: str):
                logger.info(f"Loading local embedding model from: {model_path}")
                self.model = SentenceTransformer(model_path)
                logger.info(f"Model loaded successfully with dimension {self.model.get_sentence_embedding_dimension()}")
            
            def __call__(self, input):  # MUST be 'input' not 'texts'
                # Handle the input parameter correctly
                texts = input if isinstance(input, list) else [input]
                embeddings = self.model.encode(texts, show_progress_bar=False)
                return embeddings.tolist()
        
        local_model_path = "./model_cache/all-MiniLM-L6-v2"
        if not os.path.exists(local_model_path):
            raise FileNotFoundError(f"Local model not found at {local_model_path}")
        
        embed_fn = FixedEmbeddingFunction(local_model_path)
        
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Created/loaded collection: {collection_name}")
        
        return client, collection
    except Exception as e:
        logger.error(f"Failed to create/load collection '{collection_name}': {e}")
        raise

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 120) -> List[str]:
    if not text or not text.strip():
        return []
    text = text.replace("\r\n", "\n").strip()
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk)
        start = end - overlap  # overlap
        if start <= 0 or start >= end:
            break
    return chunks


def upsert_rules_file(collection, path: str, source_id: Optional[str] = None) -> int:
    """Index a plain text / markdown rules file (chunked)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Rules file not found: {path}")
    
    source_id = source_id or os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            full = f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(path, "r", encoding="latin-1") as f:
            full = f.read()
    
    if not full.strip():
        logger.warning(f"Rules file is empty: {path}")
        return 0
    
    chunks = chunk_text(full, chunk_size=1200, overlap=150)
    if not chunks:
        logger.warning(f"No chunks generated from rules file: {path}")
        return 0
    
    ids = [f"rules::{source_id}::chunk::{i}" for i in range(len(chunks))]
    metadatas = [
        {"kind": "rules", "file": source_id, "chunk_index": i, "source": "rules_file"}
        for i in range(len(chunks))
    ]
    collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
    logger.info("Indexed %s rule chunks from %s", len(chunks), path)
    return len(chunks)


def row_to_text(row: pd.Series) -> str:
    # Convert a CSV row to a simple readable sentence-ish block
    parts = []
    for col, val in row.items():
        if pd.isna(val) or val == "":
            continue
        parts.append(f"{col}: {val}")
    return " | ".join(parts)


def upsert_csv_file(collection, path: str, source_id: Optional[str] = None, limit: Optional[int] = None) -> int:
    """Index each CSV row as a separate document."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"CSV file not found: {path}")
    
    source_id = source_id or os.path.basename(path)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.error(f"Failed to read CSV file {path}: {e}")
        raise
    
    if df.empty:
        logger.warning(f"CSV file is empty: {path}")
        return 0
    
    if limit is not None:
        df = df.head(limit)
    
    docs = []
    for idx, row in df.iterrows():
        text = row_to_text(row)
        if text.strip():  # Only add non-empty rows
            docs.append(text)
    
    if not docs:
        logger.warning(f"No valid rows found in CSV: {path}")
        return 0
    
    ids = [f"csv::{source_id}::row::{i}" for i in range(len(docs))]
    metadatas = [
        {"kind": "csv", "file": source_id, "row_index": i, "source": "csv_file"}
        for i in range(len(docs))
    ]
    collection.upsert(documents=docs, metadatas=metadatas, ids=ids)
    logger.info("Indexed %s CSV rows from %s", len(docs), path)
    return len(docs)


def query_top_k(collection, query: str, top_k: int = 6, where: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
    """Query the vector DB and return (documents, metadatas, distances)."""
    if not query or not query.strip():
        return [], [], []
    
    res = collection.query(query_texts=[query], n_results=top_k, where=where or {})
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    return docs, metas, dists


def build_context_block(kind: str, docs: List[str], metas: List[Dict[str, Any]], dists: List[float]) -> str:
    """Pretty-print a small, labeled context block."""
    if not docs:
        return f"### {kind.upper()} CONTEXT\nNo relevant content found."
    
    lines = [f"### {kind.upper()} CONTEXT (top {len(docs)})"]
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
        where = ", ".join([f"{k}={v}" for k, v in meta.items()])
        lines.append(f"- [{i}] (score={1.0 - dist:.3f}) {where}\n  {doc[:200]}...")
    return "\n".join(lines)


# =======================================
# Action items prompt
# =======================================

ACTION_ITEMS_INSTRUCTIONS = """You are an expert assistant for home improvement projects.
Using the provided RULES and DATA contexts, produce **exactly five** actionable items that comply with the rules.

Each item must be specific and implementable (what, why, how). Avoid marketing language. No duplicate items.
Return a single JSON object with the following schema:

{
  "focus": "<short phrase capturing the user's goal>",
  "items": [
    {
      "title": "<concise imperative>",
      "rationale": "<1-2 sentences referencing relevant rules or data>",
      "steps": ["<ordered step>", "..."],
      "dependencies": ["<optional blocking dependency>", "..."],
      "owner": "<role or person if clear, else 'Unassigned'>",
      "due": "<ISO date if a due date can be inferred; else null>"
    },
    ...
  ]
}

Constraints:
- ALWAYS return valid JSON parsable with a standard JSON parser.
- If a due date is not inferable, set "due" to null.
- Always return exactly five objects in "items" (no more, no less).
"""


def make_messages(user_question: str, rules_ctx: str, data_ctx: str) -> List[Dict[str, str]]:
    system_msg = {
        "role": "system",
        "content": "You are a helpful assistant for home improvement. Follow the user's organization rules strictly.",
    }
    user_msg = {
        "role": "user",
        "content": f"""{ACTION_ITEMS_INSTRUCTIONS}

USER QUESTION:
{user_question}

---
RULES:
{rules_ctx}

---
DATA:
{data_ctx}
""",
    }
    return [system_msg, user_msg]


# =======================================
# CLI
# =======================================

@dataclasses.dataclass
class Args:
    csv: Optional[str]
    rules: Optional[str]
    question: str
    collection_name: str = "leads_kb"
    persist: str = "./chroma_store"
    top_k: int = 6
    top_k_rules: Optional[int] = None
    top_k_csv: Optional[int] = None
    base_url: str = "https://apis-b2b-stage.lowes.com/v1"
    token_url: Optional[str] = None
    chat_url: Optional[str] = None
    model: str = "chatgpt_4o"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    out: Optional[str] = None
    reindex: bool = False
    csv_limit: Optional[int] = None


def parse_args() -> Args:
    p = argparse.ArgumentParser(description="Lowes RAG + Action Items app")
    p.add_argument("--csv", type=str, default=None, help="Path to CSV to index")

    p.add_argument(
        '--collection-name',
        default=os.getenv('CHROMA_COLLECTION', 'leads_kb'),
        help='Chroma collection name (3-63 chars, alnum/_/-). Default: leads_kb'
    )
    p.add_argument("--rules", type=str, default=None, help="Path to rules .txt/.md file to index")
    p.add_argument("--question", type=str, required=True, help="User question / task to generate action items for")
    p.add_argument("--persist", type=str, default="./chroma_store", help="Chroma persistence dir")
    p.add_argument("--top-k", type=int, default=6, help="Top-K results to retrieve (per source)")
    p.add_argument("--top-k-rules", type=int, default=None, help="Override Top-K for rules")
    p.add_argument("--top-k-csv", type=int, default=None, help="Override Top-K for CSV")
    p.add_argument("--base-url", type=str, default="https://apis-b2b-stage.lowes.com/v1", help="Base URL (no trailing slash)")
    p.add_argument("--token-url", type=str, default=None, help="Override token URL")
    p.add_argument("--chat-url", type=str, default=None, help="Override chat URL")
    p.add_argument("--model", type=str, default="chatgpt_4o", help="Model name (default: chatgpt_4o)")
    p.add_argument("--client-id", type=str, default=None, help="OAuth client_id (else env LOWES_CLIENT_ID)")
    p.add_argument("--client-secret", type=str, default=None, help="OAuth client_secret (else env LOWES_CLIENT_SECRET)")
    p.add_argument("--out", type=str, default=None, help="Write assistant JSON to this path")
    p.add_argument("--reindex", action="store_true", help="Drop and rebuild collection before indexing")
    p.add_argument("--csv-limit", type=int, default=None, help="Limit number of CSV rows to index (debug)")
    ns = p.parse_args()

    token_url = ns.token_url or f"{ns.base_url}/oauthprovider/oauth2/token"
    chat_url = ns.chat_url or f"{ns.base_url}/chat/completions"

    client_id = ns.client_id or os.getenv("LOWES_CLIENT_ID")
    client_secret = ns.client_secret or os.getenv("LOWES_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: Missing credentials. Provide --client-id/--client-secret or set env LOWES_CLIENT_ID and LOWES_CLIENT_SECRET.")
        sys.exit(2)

    return Args(
        csv=ns.csv,
        rules=ns.rules,
        question=ns.question,
        collection_name=ns.collection_name,
        persist=ns.persist,
        top_k=ns.top_k,
        top_k_rules=ns.top_k_rules,
        top_k_csv=ns.top_k_csv,
        base_url=ns.base_url,
        token_url=token_url,
        chat_url=chat_url,
        model=ns.model,
        client_id=client_id,
        client_secret=client_secret,
        out=ns.out,
        reindex=ns.reindex,
        csv_limit=ns.csv_limit,
    )


def maybe_recreate_collection(persist_dir: str, name: str = "leads_kb", enabled: bool = False):
    if not enabled:
        return
    try:
        client = chromadb.PersistentClient(path=persist_dir)
    except Exception:
        client = chromadb.Client()
    try:
        client.delete_collection(name)
        logger.info("Dropped existing Chroma collection '%s'", name)
    except Exception:
        pass  # it's fine if it doesn't exist


def main():
    args = parse_args()

    # Validate input files
    if args.csv and not os.path.isfile(args.csv):
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)
    if args.rules and not os.path.isfile(args.rules):
        logger.error(f"Rules file not found: {args.rules}")
        sys.exit(1)

    # Build Chroma collection
    if args.reindex:
        maybe_recreate_collection(args.persist, args.collection_name, enabled=True)
    
    try:
        client, collection = build_chroma_collection(args.persist, args.collection_name)
    except Exception as e:
        logger.error(f"Failed to build Chroma collection: {e}")
        sys.exit(1)

    # Index files if provided
    try:
        if args.rules:
            rule_count = upsert_rules_file(collection, args.rules)
            if rule_count == 0:
                logger.warning("No rules were indexed")
    except Exception as e:
        logger.error(f"Failed to index rules file: {e}")
        sys.exit(1)

    try:
        if args.csv:
            csv_count = upsert_csv_file(collection, args.csv, limit=args.csv_limit)
            if csv_count == 0:
                logger.warning("No CSV data was indexed")
    except Exception as e:
        logger.error(f"Failed to index CSV file: {e}")
        sys.exit(1)

    # Check if any data was indexed
    if not args.csv and not args.rules:
        logger.warning("No data files provided for indexing")

    # Prepare retrieval
    k_rules = args.top_k_rules or args.top_k
    k_csv = args.top_k_csv or args.top_k

    # Retrieve contexts
    try:
        rules_docs, rules_meta, rules_d = query_top_k(collection, args.question, top_k=k_rules, where={"kind": "rules"})
        csv_docs, csv_meta, csv_d = query_top_k(collection, args.question, top_k=k_csv, where={"kind": "csv"})
    except Exception as e:
        logger.error(f"Failed to query collection: {e}")
        sys.exit(1)

    rules_ctx = build_context_block("RULES", rules_docs, rules_meta, rules_d) if rules_docs else "No rules data available"
    data_ctx = build_context_block("DATA", csv_docs, csv_meta, csv_d) if csv_docs else "No CSV data available"

    # Compose messages and call chat API
    messages = make_messages(args.question, rules_ctx, data_ctx)

    auth = None
    chat = None
    try:
        auth = LowesAuthClient(client_id=args.client_id, client_secret=args.client_secret, token_url=args.token_url)
        chat = LowesAIClient(auth=auth, chat_url=args.chat_url, model=args.model)

        logger.info("Calling chat model '%s' ...", args.model)
        response = chat.chat(messages, stream=False)
        text = LowesAIClient.extract_text(response)
    except Exception as e:
        logger.error(f"Chat API call failed: {e}")
        sys.exit(1)
    finally:
        # Clean up sessions
        if chat:
            chat.close()
        if auth:
            auth.close()

    # Try to parse JSON
    parsed: Optional[Dict[str, Any]] = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Assistant did not return valid JSON: {e}")
        parsed = {"raw_text": text}

    # Save output
    if args.out:
        try:
            out_dir = os.path.dirname(args.out)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            logger.info("Wrote assistant response to %s", args.out)
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")

    # Print to console (pretty)
    print("\n=== ACTION ITEMS (assistant) ===")
    if parsed and "items" in parsed:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)
