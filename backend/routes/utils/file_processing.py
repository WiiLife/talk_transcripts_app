import fitz
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import logging
from qdrant_client.http.models import PointStruct
import tempfile
import shutil
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

CHUNK_SIZE=int(os.environ.get("CHUNK_SIZE", 800))
OVERLAP=int(os.environ.get("OVERLAP", 100))
SENTENCE_TRANSFORMER_MODEL_NAME=os.environ.get("SENTENCE_TRANSFORMER_MODEL_NAME", "all-MiniLM-L6-v2")

# Initialize model once at startup (but make it lazy)
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence transformer model...")
        _model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL_NAME)
        logger.info("Model loaded successfully")
    return _model

def extract_text(pdf_path):
    logger.info(f"Extracting text from PDF: {pdf_path}")
    text = ""
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):  # type: ignore
            page_text = page.get_text()
            text += page_text
            if (i + 1) % 10 == 0:  # Log progress every 10 pages
                logger.info(f"Processed {i + 1} pages...")
    logger.info(f"Extracted {len(text)} characters of text")
    return text

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    logger.info(f"Chunking text into segments of {chunk_size} chars with {overlap} overlap")
    chunks = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap
    
    logger.info(f"Created {len(chunks)} text chunks")
    return chunks


def embed_chunks(chunks):
    logger.info(f"Generating embeddings for {len(chunks)} chunks")
    model = get_model()
    embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)
    logger.info("Embeddings generated successfully")
    return embeddings.astype("float32")


def process_pdf_file(pdf_file_stream, filename: str, collection_name: str):
    """
    Process a PDF file stream and return points ready for vector database insertion.
    
    Args:
        pdf_file_stream: The file stream (SpooledTemporaryFile)
        filename: The original filename of the uploaded file
        collection_name: Name of the collection/document
        
    Returns:
        List of PointStruct objects ready for upsert
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(pdf_file_stream, tmp)
        temp_pdf_path = tmp.name
        
    try:
        # Extract and process text
        text = extract_text(temp_pdf_path)
        chunked_text = chunk_text(text)
        embedded_chunks = embed_chunks(chunked_text)
        
        # Create points for vector database
        points = []
        for i, (vect, text_chunk) in enumerate(zip(embedded_chunks, chunked_text)):
            points.append(
                PointStruct(
                    id=i,  # Start from 0 for each new collection
                    vector=vect,
                    payload={
                        "text": text_chunk,
                        "source": filename,  # Use the passed filename
                        "document": collection_name
                    }
                )
            )
        
        return points
        
    finally:
        # Clean up temporary file
        os.unlink(temp_pdf_path)

def process_txt_file(txt_file_stream, filename: str, collection_name: str):
    """
    Process a TXT file stream and return points ready for vector database insertion.
    
    Args:
        txt_file_stream: The file stream (SpooledTemporaryFile)
        filename: The original filename of the uploaded file
        collection_name: Name of the collection/document
        
    Returns:
        List of PointStruct objects ready for upsert
    """
    # Read text directly from the file stream
    text = txt_file_stream.read().decode('utf-8')
    
    try:
        # Process text (chunk and embed)
        chunked_text = chunk_text(text)
        embedded_chunks = embed_chunks(chunked_text)
        
        # Create points for vector database
        points = []
        for i, (vect, text_chunk) in enumerate(zip(embedded_chunks, chunked_text)):
            points.append(
                PointStruct(
                    id=i,  # Start from 0 for each new collection
                    vector=vect,
                    payload={
                        "text": text_chunk,
                        "source": filename,
                        "document": collection_name
                    }
                )
            )
        
        return points
        
    except Exception as e:
        logger.error(f"Error processing TXT file {filename}: {e}")
        raise
