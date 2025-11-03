# pgx-lower Query Execution

Simple interface to execute queries on pgx-lower with MLIR IR extraction.

## Quick Start

```python
from pgx_lower_query import execute_pgx_lower_query

# Execute a simple SELECT query
result = await execute_pgx_lower_query(
    query="SELECT * FROM users WHERE id > 10"
)

# Access results
print(result["query"])                    # The executed query
print(result["database"])                 # Database name
print(result["query_results"]["content"]) # Query results
print(result["ir_stages"])                # MLIR IR stages
```

## Response Structure

```python
{
    "query": "SELECT * FROM users WHERE id > 10",
    "database": "postgres",
    "query_results": {
        "title": "Query Results",
        "content": "id | name\n----+-------\n11 | Alice",
        "row_count": 1
    },
    "ir_stages": [
        {
            "stage": "Phase 3a before optimization",
            "filename": "pgx_lower_Phase 3a before optimization_20251102_075918.mlir",
            "content": "module { ... }"  # Full MLIR IR
        },
        {
            "stage": "Phase 3a AFTER: RelAlg -> DB+DSA+Util",
            "filename": "...",
            "content": "..."
        },
        # ... more stages
    ]
}
```

## IR Stages Included

Each query generates MLIR IR at these compilation stages:

1. **Phase 3a (RelAlg)** - High-level relational operations
   - `relalg.basetable` - Table access
   - `relalg.filter` - WHERE clause
   - `relalg.join` - JOIN operations
   - `relalg.sort` - ORDER BY
   - `relalg.limit` - LIMIT clause
   - `relalg.aggregate` - GROUP BY
   - `relalg.materialize` - Result materialization

2. **Phase 3a (DB+DSA+Util)** - Mid-level dialect operations
   - `dsa.create_ds` - Data structure creation
   - `dsa.scan_source` - Table scanning
   - `dsa.for` - Iteration
   - `db.nullable_get_val` - Null handling
   - `dsa.sort` - Sorting
   - `util.pack/get_tuple` - Tuple operations

3. **Phase 3c (LLVM)** - Low-level machine IR
   - `llvm.func` - Function definitions
   - `llvm.call` - Runtime function calls
   - `llvm.br`, `llvm.cond_br` - Control flow
   - `llvm.alloca`, `llvm.store`, `llvm.load` - Memory operations

## Usage in REST API

The `/query/ir` endpoint uses this module:

```bash
curl -X POST http://localhost:8000/query/ir \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users LIMIT 5"}'
```

Response:
```json
{
  "query": "SELECT * FROM users LIMIT 5",
  "database": "postgres",
  "num_stages": 9,
  "query_results": {
    "title": "Query Results",
    "content": "...",
    "row_count": 5
  },
  "ir_stages": [...]
}
```

## Requirements

### Query Requirements

- **SELECT only** - INSERT, UPDATE, DELETE rejected
- **MLIR compatible** - Must include one of:
  - Table scan (SeqScan, IndexScan)
  - Aggregation (COUNT, SUM, etc.)
  - Join (INNER, LEFT, etc.)
  - Limit (LIMIT clause)
  - Sorting (ORDER BY)

Simple constants like `SELECT 1` won't generate IR (not MLIR-compatible).

### Database Connection

Set environment variables:

```bash
PGX_LOWER_HOST=localhost         # PostgreSQL host
PGX_LOWER_PORT=54320             # PostgreSQL port
PGX_LOWER_USER=postgres          # PostgreSQL user
PGX_LOWER_PASSWORD=              # PostgreSQL password
PGX_LOWER_CONTAINER=pgx-lower-dev  # Docker container name
USE_DOCKER_EXEC=true             # Extract IR files from Docker
```

## Advanced Usage

### Custom Executor

```python
from pgx_lower_query import PgxLowerQueryExecutor

executor = PgxLowerQueryExecutor(
    host="localhost",
    port=54320,
    user="postgres",
    container_name="pgx-lower-dev",
    use_docker_exec=True
)

await executor.connect()
result = await executor.execute("SELECT * FROM table_name")
await executor.disconnect()
```

### Error Handling

```python
from pgx_lower_query import execute_pgx_lower_query

try:
    result = await execute_pgx_lower_query(query)
except ValueError as e:
    # Query validation error (write operations, etc.)
    print(f"Invalid query: {e}")
except asyncpg.PostgresError as e:
    # Database error
    print(f"Database error: {e}")
except Exception as e:
    # Other errors (connection, IR extraction, etc.)
    print(f"Error: {e}")
```

## Integration Examples

### Flask/FastAPI Endpoint

```python
from pgx_lower_query import execute_pgx_lower_query

@app.post("/compile")
async def compile_query(request):
    query = request.json["query"]
    result = await execute_pgx_lower_query(query)
    return {"ir": result["ir_stages"], "results": result["query_results"]}
```

### CLI Tool

```python
import asyncio
from pgx_lower_query import execute_pgx_lower_query

async def main():
    query = "SELECT id, name FROM users ORDER BY id"
    result = await execute_pgx_lower_query(query)
    
    # Print results
    print(result["query_results"]["content"])
    
    # Print IR stages
    for stage in result["ir_stages"]:
        print(f"\n=== {stage['stage']} ===")
        print(stage["content"][:500])

asyncio.run(main())
```

### Jupyter Notebook

```python
import asyncio
from pgx_lower_query import execute_pgx_lower_query

# In Jupyter, use nest_asyncio
import nest_asyncio
nest_asyncio.apply()

result = await execute_pgx_lower_query("SELECT COUNT(*) FROM users")
print(result["query_results"]["content"])
```

## Debugging

Enable detailed logging:

```bash
export PGXLOWER_LOG_LEVEL=DEBUG
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
"
```

Check IR files directly in the container:

```bash
docker exec pgx-lower-dev ls -lh /tmp/pgx_ir/
docker exec pgx-lower-dev cat /tmp/pgx_ir/pgx_lower_Phase*.mlir
```
