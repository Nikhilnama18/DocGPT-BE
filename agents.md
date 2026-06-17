# DocGPT-BE Agent Guide

## What this project is

This repository is the backend for DocGPT, a project meant to showcase a RAG pipeline and query translation techniques.

The product goal is to support two document flows:

- a default document flow seeded by the backend at startup
- a user-uploaded document flow processed asynchronously

Across both flows, the user should be able to ask questions against a selected `doc_id` using a selectable query strategy.

The current repository already exposes a small FastAPI server that:

- ingests uploaded `.pdf` or `.txt` files,
- stores chunk embeddings in Qdrant,
- answers questions against one selected document via RAG,
- supports four retrieval strategies: `standard`, `multi_query`, `step_back`, and `hyde`.

The codebase is intentionally small. Almost all behavior lives in two files:

- `main.py`: API surface, startup lifecycle, upload handling, and strategy dispatch
- `rag_service.py`: document loading, chunking, embedding, Qdrant access, and RAG chains

## Target product architecture

This is the intended backend direction based on the current project plan.

### Flow 1: default document

- use a small source document, ideally under 50 pages
- process it when the server starts
- parsing -> chunking -> embeddings -> Qdrant storage
- store it under a stable `doc_id`, likely `"default"` or a fixed local identifier
- before ingesting, check whether that default `doc_id` already exists in Qdrant to avoid duplicate processing

### Flow 2: user-uploaded document

- user uploads a document, intended to be `.doc` or `.pdf`
- file size should be limited to less than `1 MB`
- raw file should be saved in blob storage
- upload metadata and processing state should be stored in Neon Postgres
- ingestion should run asynchronously
- API returns a `doc_id` immediately
- client can poll document processing status using that `doc_id`
- after processing completes, client can query by sending `question`, `strategy`, and `doc_id`

### Query strategy goal

The app is meant to demonstrate query translation techniques. The currently discussed product set is:

- `standard`
- `hyde`
- a multi-step or multi-query style strategy

The current codebase already contains:

- `standard`
- `multi_query`
- `step_back`
- `hyde`

So the implementation can evolve by aligning naming and UX with the intended product story.

### Retention and cleanup

Planned cleanup behavior:

- a recurring job runs every 24 hours
- it finds uploaded documents older than 12 hours using Neon metadata such as `created_at`
- it deletes expired source files from blob storage
- it deletes associated embeddings from Qdrant

This keeps storage and vector usage bounded as uploads grow.

### Request flow

1. FastAPI starts and runs the lifespan hook in `main.py`.
2. Startup calls `init_default_document()` from `rag_service.py`.
3. If the Qdrant collection is missing or empty, the app ingests `The Yellow Wallpaper.txt` with `doc_id="default"`.
4. Clients can upload a `.pdf` or `.txt` to `/api/upload`.
5. The upload endpoint saves the file into `data/` using a generated UUID prefix, then calls `process_document(...)`.
6. `process_document(...)` loads the file, adds `metadata["doc_id"]`, splits it into chunks, embeds the chunks, and writes them into Qdrant.
7. Clients call `/api/query` with `question`, `strategy`, and `doc_id`.
8. The backend creates a Qdrant retriever filtered on `metadata.doc_id` and runs one of the RAG strategies.

### Storage and external services

- Vector store: Qdrant Cloud via `QdrantClient` and `langchain_qdrant`
- Embeddings: OpenRouter endpoint via `OpenAIEmbeddings`
- Chat model: OpenRouter endpoint via `ChatOpenAI`
- Local upload staging: `data/`
- Default seed document: `The Yellow Wallpaper.txt`

## Current implementation vs target plan

What already exists:

- FastAPI backend
- default document startup ingestion
- upload endpoint
- Qdrant-backed retrieval
- strategy-based query endpoint
- multiple RAG strategy implementations

What is not implemented yet:

- blob storage for user uploads
- Neon Postgres table for document metadata and processing status
- asynchronous background ingestion for uploads
- upload status endpoint by `doc_id`
- cleanup job for expired documents
- deletion of expired vectors from Qdrant
- strict `< 1 MB` upload limit
- native `.doc` support
- explicit check that `doc_id="default"` exists before skipping default ingestion

## Environment variables

The app expects these keys in `.env`:

- `OPENROUTER_API_KEY`
- `Qdrant_API_KEY`
- `Qdrant_CLUSTER_URL`
- `ANONYMIZED_TELEMETRY` is present in `.env` but not used by the app code

Important: the Qdrant variable names use mixed casing exactly as shown above. If you normalize them without updating code, startup and retrieval will break.

## API surface

### `GET /health`

Returns a simple status payload.

### `POST /api/upload`

- Accepts one multipart file field named `file`
- Only allows `.pdf` and `.txt` in the current code
- Generates a UUID `doc_id`
- Saves the file to `data/{doc_id}_{original_filename}`
- Processes and indexes the file in Qdrant

Planned evolution:

- enforce a file size limit under `1 MB`
- support blob storage instead of only local staging
- persist upload metadata and status in Neon
- make ingestion asynchronous

Response includes:

- `message`
- `doc_id`

### `POST /api/query`

Request body:

```json
{
  "question": "string",
  "strategy": "standard",
  "doc_id": "default"
}
```

Supported strategies:

- `standard`
- `multi_query`
- `step_back`
- `hyde`

## RAG strategy behavior

### `standard_rag`

- retrieves top `k=3` chunks for the user question
- formats the retrieved text into a concise answer prompt

### `multi_query_rag`

- asks the LLM to create three alternative phrasings
- retrieves on the original question plus generated variants
- deduplicates chunks by `page_content`
- answers from the merged context

### `step_back_rag`

- asks the LLM for a more general version of the question
- retrieves on both the original and generalized question
- merges and deduplicates context before answering

### `hyde_rag`

- asks the LLM to generate a hypothetical answer passage
- retrieves using that hypothetical passage
- answers from the retrieved real chunks

## Files and folders worth understanding

- `main.py`: FastAPI app and endpoint wiring
- `rag_service.py`: all retrieval and ingestion logic
- `requirements.txt`: runtime dependencies
- `The Yellow Wallpaper.txt`: default document ingested on startup
- `data/`: temporary local upload storage
- `chroma_db/`: currently unused by the codebase and likely leftover from an earlier vector-store approach
- `venv/`: checked into the workspace, but `.gitignore` indicates it should normally stay untracked

## Operational caveats

- There is no automated test suite in the repo right now.
- Error handling in `main.py` wraps broad exceptions into HTTP 500 responses.
- The upload success message says "into Qdrant", which matches current code, but the repo still contains an unused `chroma_db/` folder that may confuse contributors.
- `init_default_document()` only checks whether the collection has any points, not whether `doc_id="default"` specifically exists, which does not yet match the intended architecture.
- Uploaded files are saved locally and are not cleaned up after ingestion.
- `langchain-huggingface` and `sentence-transformers` appear in `requirements.txt` but are not used by the current implementation.
- The current backend accepts `.txt`, while the future product description focuses on `.doc` and `.pdf`, so file format support needs a deliberate decision.

## Safe change guidelines for future agents

- Preserve the `doc_id` metadata path unless you also update the Qdrant payload index and filter key.
- If you add a new RAG strategy, update both `rag_service.py` and the dispatch logic in `main.py`.
- Keep startup behavior in mind before changing collection initialization; the app currently assumes it can auto-seed content at boot.
- Do not expose `.env` values in logs, docs, or commits.
- If you remove Qdrant or OpenRouter usage, also clean up the corresponding wording in comments, docs, and dependencies.

## Useful local commands

Run the API:

```bash
uvicorn main:app --reload
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Suggested next cleanup areas

- add a minimal README with setup, env, and API examples
- add tests for upload validation and query strategy dispatch
- decide whether `chroma_db/` should be deleted
- add a document metadata model and persistence layer for Neon
- add async ingestion plus a status endpoint
- decide whether uploaded source files in `data/` should be retained or replaced by blob storage
