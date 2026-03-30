import tempfile
import os 
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import shutil
import io
import PyPDF2

load_dotenv()
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
EMBEDDING_DIMENSION = os.getenv("EMBEDDING_DIMENSION")
os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


#Loading embedding model once at startup 
Embeddings = HuggingFaceEmbeddings(
    model_name = EMBEDDING_MODEL,
    model_kwargs = {"device": "cuda",  "trust_remote_code": True},
    encode_kwargs = {"normalize_embeddings": True
                     }
)


def ingest(file_bytes: bytes, document_id: int) -> int:
    """ 1.loads pdf with pypdfloader
        2. splits the document into the chunks using RecursiveCharacterTextSplitter
        3. Embed the chunks into the vector using sentence-transformer
        4. Save FAISS index to disk

    Args:
        file_bytes (bytes): Contents of the uploaded file as bytes
        document_id (int): ID of the document uplaoded

    Returns:
       chunk_size(int) : Size of the total chunks created
    """
    
    with tempfile.NamedTemporaryFile(suffix="pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
        
    try:
        loader = PyPDFLoader(tmp_path)
        pages = loader.load() #pagecontent + metadata
    finally:
        os.unlink(tmp_path)
        
    if not pages:
        raise ValueError("Could not extract any text from the PDF.")
    
    
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50,
        separators = ["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = splitter.split_documents(pages)
    
    if not chunks:
        raise ValueError("Text splitting produced no chunks.")
    
    
    
    index_path = os.path.join(FAISS_INDEX_DIR, f"doc_{document_id}")
    vectorstore = FAISS.from_documents(chunks, Embeddings)
    vectorstore.save_local(index_path)
    return len(chunks)


def load_index(document_id: int) -> FAISS:
    """Loads the saved FAISS index from the disk for a given document

    Args:
        document_id (int): Id of the document 
    Returns:
        FAISS: Vector of the chunks of the document
    """
    
    index_path = os.path.join(FAISS_INDEX_DIR, f"doc_{document_id}")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"No FAISS index found for the document {document_id}")
    
    return FAISS.load_local(index_path, Embeddings, allow_dangerous_deserialization=True)


def delete_index(docuemnt_id: int):
    """ Delete the FAISS index from the index folder of the given document id

    Args:
        docuemnt_id (int): Document ID of the document to be removed
    """

    index_path = os.path.join(FAISS_INDEX_DIR, f"doc_{docuemnt_id}")
    if os.path.exists(index_path):
        shutil.rmtree(index_path)
        
        
def get_page_count(file_bytes: bytes) -> int:
    """Quick page count without full ingestion

    Args:
        file_bytes (bytes): Bytes of the file uploaded
    Returns:
        int: No of pages in the file
    """
    
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return len(reader.pages)