import asyncio
import subprocess
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncpg
from ir_extractor import IRExtractor
from logger import logger


class PgxLowerQueryExecutor:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 54320,
        user: str = "postgres",
        password: str = "",
        container_name: str = "pgx-lower-dev",
        use_docker_exec: bool = True
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.container_name = container_name
        self.use_docker_exec = use_docker_exec
        self.conn = None
    
    async def connect(self) -> None:
        if self.conn:
            return

        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database="postgres",
            timeout=10
        )
        logger.info(f"Connected to pgx-lower at {self.host}:{self.port}")

    async def disconnect(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None
            logger.info("Disconnected from pgx-lower")
    
    def _get_ir_files_from_container(self) -> List[tuple[str, str]]:
        if not self.use_docker_exec:
            return []
        
        ir_files = []
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "find", "/tmp/pgx_ir", 
                 "-name", "pgx_lower_*.mlir", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return []
            
            filepaths = [fp.strip() for fp in result.stdout.strip().split("\n") if fp.strip()]
            
            # Read each file
            for filepath in filepaths:
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
            logger.warning(f"Failed to extract IR files from container: {e}")

        return ir_files
    
    async def execute(
        self,
        query: str,
        database: str = "postgres"
    ) -> Dict[str, Any]:
        if not self.conn:
            await self.connect()

        query_upper = query.strip().upper()
        if any(op in query_upper for op in ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]):
            raise ValueError("Query contains write operations - only SELECT queries are allowed")

        IRExtractor.ensure_ir_directory()
        removed = IRExtractor.cleanup_all_ir_files()
        logger.debug(f"Cleaned {removed} old IR files")
        
        try:
            try:
                await self.conn.execute("LOAD 'pgx_lower.so'")
            except asyncpg.PostgresError as e:
                if "already loaded" not in str(e):
                    logger.warning(f"Failed to load extension: {e}")
            
            # Enable IR logging
            try:
                await self.conn.execute("SET pgx_lower.log_enable = true")
                await self.conn.execute(
                    "SET pgx_lower.enabled_categories = 'AST_TRANSLATE,RELALG_LOWER,DB_LOWER,JIT'"
                )
            except asyncpg.PostgresError:
                logger.debug("Could not set pgx_lower logging parameters")
            
            # Execute query
            logger.debug(f"Executing query: {query[:100]}...")
            results = await self.conn.fetch(query)
            
            # Format query results
            query_content = "No results"
            if results:
                columns = list(results[0].keys())
                lines = [" | ".join(str(c) for c in columns)]
                lines.append("-" * len(lines[0]))
                for row in results:
                    lines.append(" | ".join(str(row[c]) for c in columns))
                query_content = "\n".join(lines)

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

            logger.info(f"Query executed successfully, {len(ir_stages)} IR stages generated")
            
            return {
                "query": query,
                "database": database,
                "query_results": {
                    "title": "Query Results",
                    "content": query_content,
                    "row_count": len(results) if results else 0
                },
                "ir_stages": ir_stages
            }

        finally:
            removed = IRExtractor.cleanup_all_ir_files()
            logger.debug(f"Cleaned up {removed} IR files")


_executor: Optional[PgxLowerQueryExecutor] = None


async def get_executor() -> PgxLowerQueryExecutor:
    global _executor

    if _executor is None:
        _executor = PgxLowerQueryExecutor(
            host=os.getenv("PGX_LOWER_HOST", "localhost"),
            port=int(os.getenv("PGX_LOWER_PORT", "54320")),
            user=os.getenv("PGX_LOWER_USER", "postgres"),
            password=os.getenv("PGX_LOWER_PASSWORD", ""),
            container_name=os.getenv("PGX_LOWER_CONTAINER", "pgx-lower-dev"),
            use_docker_exec=os.getenv("USE_DOCKER_EXEC", "true").lower() == "true"
        )

    return _executor


async def execute_pgx_lower_query(
    query: str,
    database: str = "postgres",
    host: Optional[str] = None,
    port: Optional[int] = None
) -> Dict[str, Any]:
    executor = await get_executor()

    if host:
        executor.host = host
    if port:
        executor.port = port

    return await executor.execute(query, database)


async def shutdown_executor() -> None:
    global _executor

    if _executor:
        await _executor.disconnect()
        _executor = None
