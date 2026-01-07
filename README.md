# Talk Transcripts App

## Project idea

This project is a work-in-progress web application for ingesting, processing, and interactively querying spoken-talk transcripts (presentations, talks, interviews). The main goal is to transform long transcript files into searchable, conversational knowledge so users can ask questions, navigate highlights, and retrieve context from large talk transcripts.

## High-level capabilities

- Chunked upload and ingestion of transcript text.
- Preprocessing pipeline to split, normalize, and store transcript chunks.
- Semantic search using vector embeddings and a vector database to find relevant chunks.
- Conversational LLM responses built on retrieved context (chat-style question answering over transcripts).
- Lightweight frontend for uploading, chatting, and browsing stored transcripts.

## Architecture overview

The repository contains two complementary backend implementations and a modern frontend:

- Frontend (frontend/): a Vite + React TypeScript app with UI components for uploads, chat, and database view.
- Backend (backend/): an earlier or experimental backend with routes for file upload and LLM response handling.
- New backend (new_backend/): a more modular server structure with controllers, clients (Redis, Qdrant), models, and routes organized for production features.

Core subsystems

- File upload & chunking: incoming transcripts are split into manageable chunks and stored in uploads for later embedding.
- Embedding & vector store: text chunks are converted to vector embeddings and indexed in a vector DB (e.g., Qdrant) for semantic retrieval.
- Retrieval + LLM orchestration: queries use semantic search to retrieve context, then an LLM is prompted with the retrieved context to produce concise answers.
- Caching & performance: Redis is used to cache intermediate results and speed up repeated queries.

## Data flow (conceptual)

1. User uploads a transcript (or uploads are created from text files).
2. The backend splits the transcript into chunks, normalizes text, and stores raw chunks.
3. Chunks are embedded and indexed into a vector database.
4. On user query, the system retrieves top-k relevant chunks from the vector DB.
5. Retrieved chunks are fed to an LLM to generate an answer, optionally using a chat history.

## Notable folders and responsibilities

- `frontend/` — UI and client-side logic (upload UI, chat UI, components).  
- `backend/` — existing API endpoints, upload and LLM response routes, utilities.  
- `new_backend/` — refactored server with `clients/` (Qdrant, Redis), `controllers/`, `routes/`, `models/`, and a `utils/` pipeline for file processing.  
- `tests/` — some unit and integration tests (work in progress).

## Current status

- Core features are present in prototype form: file chunking, uploads, basic routes, and frontend skeletons.  
- The `new_backend/` shows a more modular design aimed at production-readiness (vector DB client, Redis client, controllers).  
- End-to-end orchestration (embedding, vector indexing, robust query handling, and polished UI flows) is still in progress.

## Roadmap / next steps (high-level)

- Finalize ingestion pipeline and embedding integration.  
- Harden retrieval and LLM prompt engineering for reliable answers.  
- Add background processing for large uploads and indexing.  
- Expand frontend flows for browsing transcripts, highlights, and chat history.  
- Add comprehensive tests and CI, plus documentation for deployment and operations.

## Contributing

Contributions are welcome. Preferred areas: pipeline reliability, vector store integrations, improved UI/UX, and test coverage. Open an issue or PR to start a discussion.
