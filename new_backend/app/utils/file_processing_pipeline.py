from sentence_transformers import SentenceTransformer
from qdrant_client.http.models import PointStruct
from config.config import settings
from fastapi import UploadFile
from pathlib import Path
from typing import List
import logging
import asyncio
logging.basicConfig(level=logging.INFO)


class FileProcessingPipeline:
    def __init__(self) -> None:
        self.__embedding_model = None
        self.__logger = logging.getLogger(__name__)
        
    @property
    def embedding_model(self) -> SentenceTransformer:
        if self.__embedding_model is None:
            self.__logger.info("Loading sentence transformer model...")
            self.__embedding_model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL_NAME)
            self.__logger.info("Model loaded successfully")
        return self.__embedding_model
    
    @embedding_model.setter
    def embedding_model(self, value):
        self.__embedding_model = value
        
    def _chunk_text(self, text: str, chunk_size: int = settings.CHUNK_SIZE, overlap: int = settings.OVERLAP) -> List[str]:
        self.__logger.info(f"Chunking text into segments of {chunk_size} chars with {overlap} overlap")
        chunks = []
        start = 0
        text = text.strip()

        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap
        
        self.__logger.info(f"Created {len(chunks)} text chunks")
        return chunks
    
    def _embed_chunks(self, chunks: List[str]):
        self.__logger.info(f"Generating embeddings for {len(chunks)} chunks")
        model = self.embedding_model
        embeddings = model.encode(chunks, batch_size=settings.BATCH_SIZE, show_progress_bar=True)
        self.__logger.info("Embeddings generated successfully")
        return embeddings.astype("float32")
    
    async def chunk_text(self, text: str):
        loop = asyncio.get_running_loop()
        chunked_text = await loop.run_in_executor(None, self._chunk_text, text)
        return chunked_text
    
    async def embed_chunks(self, chunks: List[str]):
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, self._embed_chunks, chunks)
        return embeddings

    async def process_txt_file(self, file: UploadFile):
        data = file.file.read()
        text = data.decode("utf-8")
        
        chunked_text = await self.chunk_text(text)
        embeddings = await self.embed_chunks(chunked_text)
        
        points = []
        for i, (vect, text_chunk) in enumerate(zip(embeddings, chunked_text)):
            points.append(
                PointStruct(
                    id=i,
                    vector=vect,
                    payload={
                        "text": text_chunk,
                        "source": file.filename,
                        "document": Path(file.filename).stem if file.filename else ""
                    }
                )
            )
        
        return points
