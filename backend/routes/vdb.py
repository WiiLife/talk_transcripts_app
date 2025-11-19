from fastapi import APIRouter, File, UploadFile
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
import tempfile
import shutil
from dotenv import load_dotenv
import os

from .utils.pdf_processing import extract_text, chunk_text, embed_chunks
from ..models.messages import SuccessfulMessage


load_dotenv()
VECTOR_DB_COLLECTION_NAME = os.environ.get("VECTOR_DB_COLLECTION_NAME", "talks_transcripts")

route = APIRouter(prefix="/api", tags=["database_router"])
client = QdrantClient(url="http://localhost:6333")  # vectorDB: docker run -p 6333:6333 qdrant/qdrant | ui: docker run -p 3000:3000 --env QDRANT_URL=http://host.docker.internal:6333 mintplexlabs/vectoradmin
# Or on-disk
# client = QdrantClient(path="./db/data")

@route.post("/upload")
async def upload_pdf(pdf: UploadFile = File(...)):
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(pdf.file, tmp)
        temp_pdf_path = tmp.name
        
    text = extract_text(temp_pdf_path)
    chunked_text = chunk_text(text)
    embedded_chunks = embed_chunks(chunked_text)
    
    points = []
    for i, (vect, text) in enumerate(zip(embedded_chunks, chunked_text)):
        points.append(
            PointStruct(
                id=i,
                vector=vect,
                payload={
                    "text": text
                }
            )
        )

    client.upsert(
        collection_name=VECTOR_DB_COLLECTION_NAME,
        points=points
    )
    
    return SuccessfulMessage(status_code=200, detail="successfully uploaded embeddings of the PDF")
