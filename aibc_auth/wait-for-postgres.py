#!/usr/bin/env python3
import asyncpg
import asyncio
import os
import sys
import time

async def wait_for_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        sys.exit(1)
    
    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql://")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            print(f"Attempting to connect to PostgreSQL (attempt {attempt + 1}/{max_attempts})")
            conn = await asyncpg.connect(database_url)
            await conn.execute("SELECT 1")
            await conn.close()
            print("PostgreSQL is ready!")
            return True
        except Exception as e:
            print(f"PostgreSQL not ready: {e}")
            attempt += 1
            if attempt < max_attempts:
                await asyncio.sleep(2)
    
    print("Failed to connect to PostgreSQL after maximum attempts")
    sys.exit(1)

if __name__ == "__main__":
    asyncio.run(wait_for_postgres())