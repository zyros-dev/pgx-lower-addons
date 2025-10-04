import asyncpg
from typing import List
from .base import DatabaseConnector, QueryOutput

class PostgresConnector(DatabaseConnector):
    def __init__(self, host: str = "postgres", port: int = 5432,
                 user: str = "pgxuser", password: str = "pgxpassword",
                 database: str = "pgxdb"):
        super().__init__(
            name="postgres",
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.conn = None

    async def connect(self):
        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    async def disconnect(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def get_version(self) -> str:
        if not self.conn:
            await self.connect()

        result = await self.conn.fetchval("SELECT version()")
        version_parts = result.split()
        return f"{version_parts[0]} {version_parts[1]}"

    async def initialize_tables(self):
        pass

    async def _execute_query(self, query: str) -> List[QueryOutput]:
        if not self.conn:
            await self.connect()

        outputs = []
        import time

        try:
            start = time.time()
            analyze_results = await self.conn.fetch(f"EXPLAIN ANALYZE {query}")
            analyze_latency = (time.time() - start) * 1000

            analyze_content = "\n".join(row['QUERY PLAN'] for row in analyze_results)

            outputs.append(QueryOutput(
                title="Query Plan (EXPLAIN ANALYZE)",
                content=analyze_content,
                latency_ms=None
            ))

            start = time.time()
            results = await self.conn.fetch(query)
            query_latency = (time.time() - start) * 1000

            if results:
                columns = list(results[0].keys())
                table_lines = [" | ".join(columns)]
                table_lines.append("-" * len(table_lines[0]))

                for row in results:
                    row_values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                    table_lines.append(" | ".join(row_values))

                content = "\n".join(table_lines)
            else:
                content = "No results returned"

            outputs.append(QueryOutput(
                title="Query Results",
                content=content,
                latency_ms=round(query_latency, 2)
            ))

        except Exception as e:
            outputs.append(QueryOutput(
                title="SQL Error",
                content=f"{type(e).__name__}: {str(e)}",
                latency_ms=None
            ))

        return outputs
