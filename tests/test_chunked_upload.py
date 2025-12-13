import requests
import os
import math
import time
import base64
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000/api"
FILE_NAME = "test_upload.txt"
CONTENT = "Hello world! " * 10000  # ~130KB
CHUNK_SIZE = 1024 * 10  # 10KB

def test_chunked_upload():
    # 1. Prepare file and chunks
    file_size = len(CONTENT)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    print(f"Preparing to upload {FILE_NAME} ({file_size} bytes) in {total_chunks} chunks.")

    # 2. Init Upload
    init_payload = {
        "file_name": FILE_NAME,
        "file_size": file_size,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "content_type": "text/plain"
    }
    
    print("Initializing upload...")
    resp = requests.post(f"{BASE_URL}/upload/init", json=init_payload)
    if resp.status_code != 200:
        print(f"Init failed: {resp.text}")
        return
    
    data = resp.json()
    redis_uuid = data["payload"]["redis_uuid"]
    print(f"Upload initialized. Session ID: {redis_uuid}")

    # 3. Upload Chunks (with session for connection reuse)
    start_time = time.time()
    with requests.Session() as session:
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = min((i + 1) * CHUNK_SIZE, file_size)
            chunk_data = CONTENT[start:end]
            
            chunk_payload = {
                "chunk_data": chunk_data,
                "chunk_index": i,
                "file_name": FILE_NAME,
                "redis_uuid": redis_uuid
            }
            
            print(f"Uploading chunk {i+1}/{total_chunks}...")
            chunk_start = time.time()
            resp = session.post(f"{BASE_URL}/upload/chunk", json=chunk_payload)
            
            if resp.status_code != 200:
                print(f"Chunk {i} upload failed: {resp.status_code} - {resp.text}")
                return
            else:
                chunk_time = time.time() - chunk_start
                print(f"Chunk {i+1} success. Time: {chunk_time:.2f}s")

    total_time = time.time() - start_time
    print(f"All chunks uploaded in {total_time:.2f}s")

    # 4. Complete Upload
    print("Completing upload...")
    complete_payload = {
        "redis_uuid": redis_uuid
    }
    resp = requests.post(f"{BASE_URL}/upload/complete", json=complete_payload)
    
    if resp.status_code != 200:
        print(f"Completion failed: {resp.status_code} - {resp.text}")
    else:
        print("Upload completed successfully!")

# Async version for better performance
async def test_chunked_upload_async():
    file_size = len(CONTENT)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    print(f"Preparing to upload {FILE_NAME} ({file_size} bytes) in {total_chunks} chunks.")

    init_payload = {
        "file_name": FILE_NAME,
        "file_size": file_size,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "content_type": "text/plain"
    }
    
    print("Initializing upload...")
    redis_uuid = None
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/upload/init", json=init_payload) as resp:
            if resp.status != 200:  
                print(f"Init failed: {resp.status}")
                text = await resp.text()
                print(text)
                return
            
            data = await resp.json()
            redis_uuid = data["payload"]["redis_uuid"]
            print(f"Upload initialized. Session ID: {redis_uuid}")

        # 3. Upload Chunks concurrently (with limit bc server only allows for certain ammount of concurrent threads)
        start_time = time.time()
        semaphore = asyncio.Semaphore(5)
        
        async def upload_chunk(i):
            async with semaphore:
                start = i * CHUNK_SIZE
                end = min((i + 1) * CHUNK_SIZE, file_size)
                chunk_bytes = CONTENT[start:end]
                
                chunk_payload = {
                    "redis_uuid": redis_uuid,
                    "chunk_index": i,
                    "chunk_data": chunk_bytes,
                    "embed_chunk": False 
                }
                
                print(f"Uploading chunk {i+1}/{total_chunks} ({len(chunk_bytes)} bytes)...")
                chunk_start = time.time()
                async with session.post(f"{BASE_URL}/upload/chunk", json=chunk_payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        detail = await resp.body.detail
                        print(f"Chunk {i} failed: {resp.status} - {text}: {detail}")
                        return False
                    data = await resp.json()
                    chunk_time = time.time() - chunk_start
                    print(f"Chunk {i+1} success ({data.get('detail', 'OK')}). Time: {chunk_time:.2f}s")
                    return True
        
        tasks = [upload_chunk(i) for i in range(total_chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        failed = [r for r in results if isinstance(r, Exception) or r is False]
        if failed:
            print(f"Failed uploads: {len(failed)}")
            return
        
        total_time = time.time() - start_time
        print(f"All chunks uploaded in {total_time:.2f}s")

        # 4. Complete Upload
        print("Completing upload...")
        complete_payload = {"redis_uuid": redis_uuid}
        async with session.post(f"{BASE_URL}/upload/complete", json=complete_payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Completion failed: {resp.status} - {text}")
            else:
                data = await resp.json()
                print("Upload completed successfully!")
                print(f"Result: {data.get('detail', 'OK')}")

async def test_unuploaded_chunks():
    # Prepare file and chunks
    file_size = len(CONTENT)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    print(f"Preparing to upload {FILE_NAME} ({file_size} bytes) in {total_chunks} chunks.")

    # Init Upload
    init_payload = {
        "file_name": FILE_NAME,
        "file_size": file_size,
        "chunk_size": CHUNK_SIZE,
        "total_chunks": total_chunks,
        "content_type": "text/plain"
    }
    print("Initializing upload...")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/upload/init", json=init_payload) as resp:
            if resp.status!= 200:
                print(f"Init failed: {resp.status}")
                text = await resp.text()
                print(text)
                return
            data = await resp.json()
            redis_uuid = data["payload"]["redis_uuid"]
            print(f"Upload initialized. Session ID: {redis_uuid}")

        # Upload some chunks, but not all
        uploaded_chunks = []
        for i in range(total_chunks // 2):
            start = i * CHUNK_SIZE
            end = min((i + 1) * CHUNK_SIZE, file_size)
            chunk_bytes = CONTENT[start:end]
            chunk_payload = {
                "redis_uuid": redis_uuid,
                "chunk_index": i,
                "chunk_data": chunk_bytes,
                "embed_chunk": False
            }
            print(f"Uploading chunk {i+1}/{total_chunks} ({len(chunk_bytes)} bytes)...")
            async with session.post(f"{BASE_URL}/upload/chunk", json=chunk_payload) as resp:
                if resp.status!= 200:
                    print(f"Chunk {i} failed: {resp.status}")
                    text = await resp.text()
                    print(text)
                    return
                data = await resp.json()
                uploaded_chunks.append(i)

        # Check that the unuploaded chunk indexes are sent
        unuploaded_chunks = [i for i in range(total_chunks) if i not in uploaded_chunks]
        print(f"Unuploaded chunks: {unuploaded_chunks}")

        # Complete Upload
        print("Completing upload...")
        complete_payload = {"redis_uuid": redis_uuid}
        async with session.post(f"{BASE_URL}/upload/complete", json=complete_payload) as resp:
            if resp.status!= 200:
                print(f"Completion failed: {resp.status}")
                text = await resp.text()
                print(text)
                return
            data = await resp.json()
            print("Upload completed successfully!")
            print(f"Result: {data.get('detail', 'OK')}")

            # Check that the unuploaded chunk indexes are sent
            print(data)
            if "missing_indexes" not in data:
                print("Error: unuploaded_chunks not found in response")
                return
            sent_unuploaded_chunks = data.payload["missing_indexes"]
            if set(sent_unuploaded_chunks)!= set(unuploaded_chunks):
                print(f"Error: sent unuploaded chunks {sent_unuploaded_chunks} do not match expected unuploaded chunks {unuploaded_chunks}")
                return
            print("Test passed: unuploaded chunk indexes are sent correctly")

if __name__ == "__main__":
    # Run synchronous version
    # test_chunked_upload()
    # Or run async version (uncomment to use)
    # asyncio.run(test_chunked_upload_async())
    asyncio.run(test_unuploaded_chunks())
