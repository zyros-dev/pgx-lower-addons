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
    _timeout = 60.0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def execute_with_lock(self, coro, timeout: Optional[float] = None):
        timeout_val = timeout if timeout is not None else self._timeout

        async with self._lock:
            try:
                return await asyncio.wait_for(coro, timeout=timeout_val)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Query execution exceeded {timeout_val}s timeout")

class DatabaseConnector(ABC):
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
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def get_version(self) -> str:
        pass

    @abstractmethod
    async def initialize_tables(self):
        pass

    def validate_readonly_query(self, query: str) -> bool:
        query_stripped = query.strip()

        if query_stripped.count(';') > 1:
            raise ValueError("Only one SQL statement allowed")

        if query_stripped.endswith(';'):
            query_stripped = query_stripped[:-1].strip()

        if ';' in query_stripped:
            raise ValueError("Multiple SQL statements not allowed")

        query_upper = query_stripped.upper()
        query_upper = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)
        query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)

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
        pass

    async def run(self, query: str) -> QueryResult:
        if not self.validate_readonly_query(query):
            raise ValueError("Query contains write operations and is not allowed")

        outputs = await self.query_lock.execute_with_lock(self._execute_query(query))
        latency_ms = sum(output.latency_ms for output in outputs if output.latency_ms is not None)

        version = await self.get_version()

        return QueryResult(
            database=self.name,
            version=version,
            latency_ms=round(latency_ms, 2),
            outputs=outputs
        )
