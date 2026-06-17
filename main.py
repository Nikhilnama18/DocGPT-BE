import os
import shutil
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import functions from our newly created rag_service
from rag_service import process_document, standard_rag, multi_query_rag, step_back_rag, hyde_rag, init_default_document

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs when the application starts
    print("Starting up... Initializing default document if necessary.")
    init_default_document()
    yield
    # This block runs when the application shuts down
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

# Create a directory to temporarily store uploaded files
UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    question: str
    strategy: str = "standard"  # Default strategy
    doc_id: str = "default"     # default book or a specific custom upload id

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "DocGPT Backend is running!"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to upload a PDF or TXT document and process it into the vector database.
    Generates a unique doc_id for the file.
    """
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are allowed")
    
    # Generate a unique ID for this document
    doc_id = str(uuid.uuid4())
    
    # Save the file temporarily
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Process the document using our RAG service with the generated doc_id
        process_document(file_path, doc_id=doc_id)
        return {
            "message": f"Successfully processed {file.filename} into Qdrant",
            "doc_id": doc_id
        }
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
    doc_id = request.doc_id
    
    try:
        if strategy == "standard":
            answer = standard_rag(question, doc_id)
        elif strategy == "multi_query":
            answer = multi_query_rag(question, doc_id)
        elif strategy == "step_back":
            answer = step_back_rag(question, doc_id)
        elif strategy == "hyde":
            answer = hyde_rag(question, doc_id)
        else:
            raise HTTPException(status_code=400, detail=f"Strategy '{strategy}' not implemented yet. Supported: standard, multi_query, step_back, hyde")
            
        return {"question": question, "strategy": strategy, "doc_id": doc_id, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
