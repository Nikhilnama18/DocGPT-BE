import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# We use OpenRouter via the OpenAI SDK in LangChain, as OpenRouter is OpenAI-compatible.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_CLUSTER_URL")

COLLECTION_NAME = "docgpt_collection"

# Initialize the embedding model via OpenRouter.
embeddings = OpenAIEmbeddings(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="openai/text-embedding-3-small",
    chunk_size=100 # Bulk generation
)

# Initialize the LLM via OpenRouter.
llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="nvidia/nemotron-3-super-120b-a12b:free",
    temperature=0,
    max_retries=3  # Retry on transient 429 rate-limit errors from the free tier
)

# Initialize Qdrant Client
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

def ensure_payload_index():
    """
    Ensures that a keyword index exists on 'metadata.doc_id' in the Qdrant collection.
    Qdrant Cloud requires explicit payload indexes for filtered searches to work.
    This is idempotent — if the index already exists, Qdrant will simply ignore the call.
    """
    try:
        qdrant_client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="metadata.doc_id",
            field_schema=rest.PayloadSchemaType.KEYWORD,
        )
        print("Payload index on 'metadata.doc_id' ensured.")
    except Exception as e:
        # Index may already exist, which is fine
        print(f"Payload index check: {e}")

def process_document(file_path: str, doc_id: str):
    """
    Loads a PDF or TXT document, splits it into chunks, and stores it in Qdrant Cloud.
    Adds a 'doc_id' metadata to differentiate between different documents.
    """
    print(f"Processing document: {file_path} with id: {doc_id}")
    
    # 1. Load the document based on extension
    if file_path.lower().endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    elif file_path.lower().endswith('.txt'):
        loader = TextLoader(file_path)
    else:
        raise ValueError("Unsupported file type. Only PDF and TXT are supported.")
        
    docs = loader.load()
    
    # Add doc_id to metadata
    for doc in docs:
        doc.metadata["doc_id"] = doc_id
    
    # 2. Split the document into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    
    # 3. Store the chunks in the Vector Database (Qdrant)
    vectorstore = QdrantVectorStore.from_documents(
        documents=splits, 
        embedding=embeddings, 
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME
    )
    
    # 4. Ensure payload index exists for filtered queries
    ensure_payload_index()
    
    return vectorstore

def init_default_document():
    """
    Checks if the vector database collection exists and has points. If not, processes the default document.
    """
    default_doc_path = "The Yellow Wallpaper.txt"
    if os.path.exists(default_doc_path):
        try:
            collection_info = qdrant_client.get_collection(COLLECTION_NAME)
            if collection_info.points_count == 0:
                print("Qdrant collection is empty. Ingesting default document...")
                process_document(default_doc_path, doc_id="default")
            else:
                print("Qdrant collection already contains documents. Skipping default ingestion.")
                # Ensure the index exists even if we skip ingestion
                ensure_payload_index()
        except Exception:
            # If get_collection throws an exception, the collection probably doesn't exist yet
            print("Qdrant collection not found. Ingesting default document...")
            process_document(default_doc_path, doc_id="default")
    else:
        print(f"Default document '{default_doc_path}' not found. Skipping.")

def get_retriever(doc_id: str):
    """
    Returns a retriever object to query Qdrant, filtered by doc_id.
    """
    vectorstore = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    # We use Qdrant's Filter model to ensure reliable metadata filtering
    qdrant_filter = rest.Filter(
        must=[
            rest.FieldCondition(
                key="metadata.doc_id",
                match=rest.MatchValue(value=doc_id),
            )
        ]
    )
    
    # The retriever searches the database with the filter applied
    return vectorstore.as_retriever(search_kwargs={"k": 3, "filter": qdrant_filter})

# --- RAG Strategies ---

def standard_rag(question: str, doc_id: str):
    """
    A standard Retrieval-Augmented Generation query.
    1. Retrieve relevant documents from the database based on the question.
    2. Pass the documents and the question to the LLM to get an answer.
    """
    retriever = get_retriever(doc_id)
    
    # Define a prompt template telling the LLM how to behave
    template = """Use the following pieces of retrieved context to answer the question. 
    If you don't know the answer, just say that you don't know. 
    Use three sentences maximum and keep the answer concise.
    
    Context: {context}
    
    Question: {question}
    
    Answer:"""
    prompt = PromptTemplate.from_template(template)
    
    # Create the 'chain' of operations: Retriever -> Prompt -> LLM -> String Output
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
        
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain.invoke(question)
    
# --- Advanced Query Translation Strategies ---

def multi_query_rag(question: str, doc_id: str):
    """
    Multi-Query Strategy:
    Asks the LLM to generate 3 variations of the original question.
    It retrieves documents for all variations to get a broader context,
    then answers the original question.
    """
    retriever = get_retriever(doc_id)
    
    # 1. Generate multiple queries
    multi_query_prompt = PromptTemplate(
        input_variables=["question"],
        template="""You are an AI language model assistant. Your task is to generate 3 
        different versions of the given user question to retrieve relevant documents from a vector 
        database. By generating multiple perspectives on the user question, your goal is to help
        the user overcome some of the limitations of the distance-based similarity search. 
        Provide these alternative questions separated by newlines.
        Original question: {question}"""
    )
    
    generate_queries = (
        multi_query_prompt 
        | llm 
        | StrOutputParser() 
        | (lambda x: x.split("\n"))
    )
    
    # Generate the queries
    queries = generate_queries.invoke({"question": question})
    
    # 2. Retrieve documents for all queries
    unique_docs = []
    unique_contents = set()
    
    # Always include the original question
    all_queries = [question] + [q.strip() for q in queries if q.strip()]
    
    for q in all_queries:
        docs = retriever.invoke(q)
        for doc in docs:
            if doc.page_content not in unique_contents:
                unique_contents.add(doc.page_content)
                unique_docs.append(doc)
                
    # 3. Answer using the combined context
    context = "\n\n".join(doc.page_content for doc in unique_docs)
    
    answer_prompt = PromptTemplate.from_template(
        """Use the following pieces of retrieved context to answer the question.
        Context: {context}
        Question: {question}
        Answer:"""
    )
    
    answer_chain = answer_prompt | llm | StrOutputParser()
    return answer_chain.invoke({"context": context, "question": question})

def step_back_rag(question: str, doc_id: str):
    """
    Step-Back Strategy:
    Generates a more abstract, higher-level question. Retrieves documents for 
    both the original and step-back questions to get broader background context.
    """
    retriever = get_retriever(doc_id)
    
    # 1. Generate step-back question
    step_back_prompt = PromptTemplate.from_template(
        """You are an expert at world knowledge. Your task is to step back and paraphrase a question to a more general step-back question, which is easier to answer.
        Here is the question: {question}
        Step-back question:"""
    )
    
    step_back_chain = step_back_prompt | llm | StrOutputParser()
    step_back_q = step_back_chain.invoke({"question": question})
    
    # 2. Retrieve documents for both questions
    docs_original = retriever.invoke(question)
    docs_step_back = retriever.invoke(step_back_q)
    
    # Combine and deduplicate
    unique_docs = []
    unique_contents = set()
    for doc in docs_original + docs_step_back:
        if doc.page_content not in unique_contents:
            unique_contents.add(doc.page_content)
            unique_docs.append(doc)
            
    # 3. Answer using combined context
    context = "\n\n".join(doc.page_content for doc in unique_docs)
    
    answer_prompt = PromptTemplate.from_template(
        """You are an expert. Answer the question based ONLY on the provided context.
        Context: {context}
        Question: {question}
        Answer:"""
    )
    
    answer_chain = answer_prompt | llm | StrOutputParser()
    return answer_chain.invoke({"context": context, "question": question})

def hyde_rag(question: str, doc_id: str):
    """
    HyDE (Hypothetical Document Embeddings) Strategy:
    Generates a hypothetical (fake) answer to the question. 
    Uses this hypothetical answer to search the vector database for real documents,
    because the fake answer shares similar vocabulary with the real answer.
    """
    retriever = get_retriever(doc_id)
    
    # 1. Generate a hypothetical answer
    hyde_prompt = PromptTemplate.from_template(
        """Please write a passage to answer the question. It does not need to be factual, but it should sound like a real document that answers this question.
        Question: {question}
        Passage:"""
    )
    
    hyde_chain = hyde_prompt | llm | StrOutputParser()
    hypothetical_answer = hyde_chain.invoke({"question": question})
    
    # 2. Retrieve documents using the HYPOTHETICAL answer
    docs = retriever.invoke(hypothetical_answer)
    
    # 3. Answer using the retrieved REAL documents
    context = "\n\n".join(doc.page_content for doc in docs)
    
    answer_prompt = PromptTemplate.from_template(
        """Please answer the user's question based ONLY on the provided context.
        Context: {context}
        Question: {question}
        Answer:"""
    )
    
    answer_chain = answer_prompt | llm | StrOutputParser()
    return answer_chain.invoke({"context": context, "question": question})
