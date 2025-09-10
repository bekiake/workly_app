import os

# Default SQLite (async)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./workly.db")

# PostgreSQL async uchun:
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/workly"
