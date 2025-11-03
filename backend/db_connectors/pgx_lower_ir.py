import asyncpg
import asyncio
import time
import subprocess
import os
from typing import List, Dict, Optional
from .base import DatabaseConnector, QueryOutput, QueryResult
from ir_extractor import IRExtractor


class PgxLowerIRConnector(DatabaseConnector):
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 user: Optional[str] = None, password: Optional[str] = None,
                 database: Optional[str] = None, container_name: str = "pgx-lower-dev"):
        host = host or os.getenv("PGX_LOWER_HOST", "localhost")
        port = port or int(os.getenv("PGX_LOWER_PORT", "54320"))
        user = user or os.getenv("PGX_LOWER_USER", "pgxuser")
        password = password or os.getenv("PGX_LOWER_PASSWORD", "pgxpassword")
        database = database or os.getenv("PGX_LOWER_DB", "pgxdb")

        super().__init__(
            name="pgx-lower-ir",
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.conn = None
        self.container_name = container_name
        self.use_docker_exec = os.getenv("USE_DOCKER_EXEC", "false").lower() == "true"

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

        pg_version = await self.conn.fetchval("SELECT version()")
        pg_parts = pg_version.split()
        pg_ver = f"{pg_parts[0]} {pg_parts[1]}"
        pgx_version = "0.1.0"

        return f"pgx-lower {pgx_version} ({pg_ver})"

    async def initialize_tables(self):
        pass

    def _get_ir_files_from_container(self) -> List[tuple[str, str]]:
        if not self.use_docker_exec:
            return []

        ir_files = []
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "find", "/tmp/pgx_ir", "-name", "pgx_lower_*.mlir", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return []

            filepaths = [fp.strip() for fp in result.stdout.strip().split("\n") if fp.strip()]

            for filepath in filepaths:
                if not filepath:
                    continue

                result = subprocess.run(
                    ["docker", "exec", self.container_name, "cat", filepath],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    filename = filepath.split("/")[-1]
                    ir_files.append((filename, result.stdout))

        except Exception as e:
            pass

        return ir_files

    async def _execute_query(self, query: str) -> List[QueryOutput]:
        if not self.conn:
            await self.connect()

        outputs = []

        try:
            await self.conn.execute("LOAD 'pgx_lower.so'")
        except Exception:
            pass

        start = time.time()
        results = await self.conn.fetch(query)
        query_latency = (time.time() - start) * 1000

        if results:
            columns = results[0].keys()
            table_lines = [" | ".join(columns)]
            table_lines.append("-" * len(table_lines[0]))

            for row in results:
                table_lines.append(" | ".join(str(row[col]) for col in columns))

            content = "\n".join(table_lines)
        else:
            content = "No results returned"

        outputs.append(QueryOutput(
            title="Query Results",
            content=content,
            latency_ms=round(query_latency, 2)
        ))

        start = time.time()
        plan_results = await self.conn.fetch(f"EXPLAIN {query}")
        plan_latency = (time.time() - start) * 1000

        plan_content = "\n".join(row['QUERY PLAN'] for row in plan_results)


        outputs.append(QueryOutput(
            title="Query Plan",
            content=plan_content,
            latency_ms=round(plan_latency, 2)
        ))

        return outputs

    async def execute_query_with_ir(self, query: str) -> Dict:
        if not self.validate_readonly_query(query):
            raise ValueError("Query contains write operations and is not allowed")

        if not self.conn:
            await self.connect()

        IRExtractor.ensure_ir_directory()

        removed = IRExtractor.cleanup_all_ir_files()

        try:
            await self.conn.execute("SET pgx_lower.log_enable = true;")
            await self.conn.execute(
                "SET pgx_lower.enabled_categories = 'AST_TRANSLATE,RELALG_LOWER,DB_LOWER,JIT';"
            )

            outputs = await self.query_lock.execute_with_lock(
                self._execute_query(query)
            )

            await asyncio.sleep(0.1)

            if self.use_docker_exec:
                ir_files = self._get_ir_files_from_container()
                ir_stages = [
                    {
                        "stage": IRExtractor.parse_ir_stage_name(filename),
                        "filename": filename,
                        "content": content
                    }
                    for filename, content in ir_files
                ]
            else:
                ir_stages = IRExtractor.extract_ir_stages()

            version = await self.get_version()

            latency_ms = sum(output.latency_ms for output in outputs
                           if output.latency_ms is not None)

            query_result = QueryResult(
                database=self.name,
                version=version,
                latency_ms=round(latency_ms, 2),
                outputs=outputs
            )

            return {
                "result": query_result,
                "ir_stages": ir_stages
            }

        finally:
            removed = IRExtractor.cleanup_all_ir_files()
