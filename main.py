from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cleanup_service import start_cleanup_scheduler
from document_repository import get_document_by_id

# Import functions from our newly created rag_service
from rag_service import (
    standard_rag,
    multi_query_rag,
    step_back_rag,
    hyde_rag,
    init_default_document,
    process_uploaded_document_task,
)
from upload_service import create_uploaded_document

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs when the application starts
    scheduler = None
    print("Starting up... Initializing default document if necessary.")
    init_default_document()
    scheduler = start_cleanup_scheduler()
    try:
        yield
    finally:
        # This block runs when the application shuts down
        if scheduler:
            scheduler.shutdown(wait=False)
        print("Shutting down...")

app = FastAPI(
    title="DocGPT API",
    description="Backend API for the DocGPT RAG application",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    strategy: str = "standard"  # Default strategy
    document_id: str = "default"  # "default" or a UUID string for uploaded documents

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "DocGPT Backend is running!"}

@app.post("/api/upload", status_code=202)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Endpoint to upload a document, store it in Cloudflare R2,
    persist metadata in Neon Postgres, and queue it for background processing.
    """
    try:
        response_payload, task_payload = await create_uploaded_document(file)
        background_tasks.add_task(process_uploaded_document_task, **task_payload)
        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/document/{document_id}/status")
async def get_document_status(document_id: str):
    """
    Returns the current processing status for an uploaded document.
    """
    try:
        document = get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "document_id": str(document["id"]),
            "status": document["status"],
            "chunk_count": document["chunk_count"],
            "error_message": document["error_message"],
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
            "expires_at": document["expires_at"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_document(request: QueryRequest):
    """
    Endpoint to ask a question to the document using different RAG strategies.
    Supported strategies: standard, multi_query, step_back, hyde
    """
    question = request.question
    strategy = request.strategy
    document_id = request.document_id
    
    try:
        if strategy == "standard":
            answer = standard_rag(question, document_id)
        elif strategy == "multi_query":
            answer = multi_query_rag(question, document_id)
        elif strategy == "step_back":
            answer = step_back_rag(question, document_id)
        elif strategy == "hyde":
            answer = hyde_rag(question, document_id)
        else:
            raise HTTPException(status_code=400, detail=f"Strategy '{strategy}' not implemented yet. Supported: standard, multi_query, step_back, hyde")
            
        return {"question": question, "strategy": strategy, "document_id": document_id, "answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
