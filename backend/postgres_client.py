import asyncpg


pg_client = asyncpg.create_pool(user="postgres", password="postgres", database="postgres", host="localhost", port=5432) # docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 -v postgres-data:/var/lib/postgresql/data postgres:15
