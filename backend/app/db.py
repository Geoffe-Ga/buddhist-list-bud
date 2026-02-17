import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]


def get_client() -> AsyncIOMotorClient:  # type: ignore[type-arg]
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    db_name = os.getenv("MONGO_DB", "buddhist_dhammas")
    return get_client()[db_name]


def reset_client() -> None:
    """Reset the cached client. Used by tests to avoid stale event loops."""
    global _client
    _client = None
