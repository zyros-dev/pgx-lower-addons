import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import re
from datetime import datetime

@dataclass
class QueryOutput:
    title: str
    content: str
    latency_ms: Optional[float] = None

@dataclass
class QueryResult:
    database: str
    version: str
    latency_ms: float
    outputs: List[QueryOutput]

class QueryLock:
    _instance = None
    _lock: asyncio.Lock
    _timeout = 60.0  # 60 second timeout

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def execute_with_lock(self, coro, timeout: Optional[float] = None):
        """Execute a coroutine with a lock and timeout."""
        timeout_val = timeout if timeout is not None else self._timeout

        async with self._lock:
            try:
                return await asyncio.wait_for(coro, timeout=timeout_val)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query execution exceeded {timeout_val}s timeout")

class DatabaseConnector(ABC):
    """Base class for database connectors."""

    def __init__(self, name: str, host: str, port: int, user: str, password: str, database: str):
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.query_lock = QueryLock()

    @abstractmethod
    async def connect(self):
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection to the database."""
        pass

    @abstractmethod
    async def get_version(self) -> str:
        """Get database version string."""
        pass

    @abstractmethod
    async def initialize_tables(self):
        """Initialize required tables/schema."""
        pass

    def validate_readonly_query(self, query: str) -> bool:
        """Validate that a query is read-only."""
        query_upper = query.strip().upper()

        # Remove comments
        query_upper = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)
        query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)

        # Check for write operations
        write_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
        ]

        for keyword in write_keywords:
            if re.search(rf'\b{keyword}\b', query_upper):
                return False

        return True

    @abstractmethod
    async def _execute_query(self, query: str) -> List[QueryOutput]:
        """Execute query and return outputs. Must be implemented by subclasses."""
        pass

    async def run(self, query: str) -> QueryResult:
        """Execute a query with lock and validation."""
        # Validate query is read-only
        if not self.validate_readonly_query(query):
            raise ValueError("Query contains write operations and is not allowed")

        # Execute with lock and timeout
        outputs = await self.query_lock.execute_with_lock(self._execute_query(query))

        # Sum only non-None latencies from outputs (excludes EXPLAIN ANALYZE)
        latency_ms = sum(output.latency_ms for output in outputs if output.latency_ms is not None)

        version = await self.get_version()

        return QueryResult(
            database=self.name,
            version=version,
            latency_ms=round(latency_ms, 2),
            outputs=outputs
        )
