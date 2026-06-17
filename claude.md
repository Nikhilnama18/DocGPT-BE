# Claude Notes For This Repo

## Quick mental model

This repo is the backend slice of DocGPT, a project to demonstrate RAG and query translation patterns incrementally.

Target product shape:

- one default document ingested on server startup
- one user-upload flow that returns a document `id` and processes asynchronously
- querying by `question + strategy + document_id`
- short-lived uploaded documents cleaned up automatically later

Current implementation shape:

- single-service FastAPI backend for RAG over one selected document at a time
- `main.py` owns HTTP endpoints and startup
- `rag_service.py` owns ingestion, retrieval, and prompting
- Qdrant is the real vector store
- OpenRouter is used through LangChain's OpenAI-compatible clients

If you need to understand behavior, read those two Python files first.

## Most important invariants

- Every indexed chunk must carry `metadata["document_id"]`
- Every query must retrieve with the Qdrant filter on `metadata.document_id`
- Startup may ingest `The Yellow Wallpaper.txt` as the default corpus
- Supported user-visible strategies are only `standard`, `multi_query`, `step_back`, and `hyde`

Breaking any of those changes user behavior immediately.

## Product intent to preserve

- The default document flow should avoid duplicate default ingestion by checking whether the default document already exists.
- The uploaded document flow should eventually be async and status-driven.
- Uploads are intended to be temporary, with later cleanup from blob storage and Qdrant.
- Neon Postgres is intended to become the source of truth for upload metadata, lifecycle, and expiry.
- For the demo scope, keep this in one `documents` table unless a second table becomes truly necessary.

## How the backend works

### Startup

`main.py` uses a FastAPI lifespan hook that calls `init_default_document()`.

That function:

- checks whether the Qdrant collection exists,
- ingests `The Yellow Wallpaper.txt` if the collection is missing or empty,
- otherwise ensures a payload index exists on `metadata.document_id`.

### Uploads

`POST /api/upload`:

- currently accepts `.pdf` and `.txt` only
- creates a UUID `id`
- uploads the raw file to R2
- stores metadata in Postgres with `status = UPLOADED`

`process_document(...)`:

- uses `PyPDFLoader` or `TextLoader`
- attaches `document_id` to each loaded document
- splits text with `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`
- writes embeddings into the `docgpt_collection` Qdrant collection

### Queries

`POST /api/query`:

- reads `question`, `strategy`, and `document_id`
- dispatches to one RAG function
- returns the final answer string

The shared retriever is built in `get_retriever(document_id)` and uses:

- `QdrantVectorStore`
- `k=3`
- `rest.Filter`
- `key="metadata.document_id"`

## Environment assumptions

Required `.env` keys:

- `OPENROUTER_API_KEY`
- `Qdrant_API_KEY`
- `Qdrant_CLUSTER_URL`

Watch the casing. The code does not use uppercase Qdrant variable names.

## Planned architecture that is not built yet

- blob storage for uploaded source files
- Neon Postgres table keyed by `id`
- async ingestion job for uploads
- status endpoint for polling ingestion progress
- upload validation for `< 1 MB`
- expiry cleanup job running periodically, potentially every few days in the demo
- deletion of expired blobs and their Qdrant vectors
- likely support for `.doc` in addition to `.pdf`

## Things that look stale or inconsistent

- `README.md` is only a one-line placeholder
- `chroma_db/` exists, but current code does not use Chroma at all
- `langchain-huggingface` and `sentence-transformers` are installed but unused
- `venv/` and `__pycache__/` exist locally even though `.gitignore` suggests they should not be part of normal source control flow

## If you are asked to modify this project

- For new query strategies: add a function in `rag_service.py`, then wire it into `main.py`
- For retrieval bugs: check env vars, Qdrant connectivity, collection existence, payload index, and `document_id` filter logic
- For upload bugs: check file extension validation, write permissions to `data/`, and loader selection
- For answer quality issues: inspect the prompt template, chunking settings, and retriever `k`
- For roadmap work: keep the product split clear between "default seeded doc" and "async uploaded doc"

## Things to be careful about

- `init_default_document()` treats "collection has any points" as enough to skip default ingestion; it does not verify that the default document itself exists in the collection
- uploaded files remain in `data/` after processing
- broad `except Exception` blocks can hide the original failure category from API clients
- changing metadata structure requires coordinated updates to ingestion, indexing, and retrieval filtering
- the intended product mentions temporary uploads plus cleanup, but the current code has no lifecycle management yet

## Recommended first reads

1. `main.py`
2. `rag_service.py`
3. `requirements.txt`
4. `README.md`

## Recommended first improvements

- expand `README.md`
- add tests around endpoints and strategy routing
- add a document-status persistence model in Neon
- add async ingestion and a polling endpoint
- add cleanup or retention rules for uploaded source files
- remove stale folders or dependencies if they are truly unused
