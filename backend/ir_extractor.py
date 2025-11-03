import glob
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import asyncio


class IRExtractor:
    IR_TEMP_DIR = "/tmp/pgx_ir"
    IR_FILE_PATTERN = "pgx_lower_*.mlir"

    @staticmethod
    def ensure_ir_directory() -> None:
        Path(IRExtractor.IR_TEMP_DIR).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def cleanup_all_ir_files() -> int:
        pattern = os.path.join(IRExtractor.IR_TEMP_DIR, IRExtractor.IR_FILE_PATTERN)
        files = glob.glob(pattern)

        removed_count = 0
        for filepath in files:
            try:
                os.remove(filepath)
                removed_count += 1
            except OSError as e:
                pass

        return removed_count

    @staticmethod
    def collect_ir_files() -> List[tuple[str, str]]:
        pattern = os.path.join(IRExtractor.IR_TEMP_DIR, IRExtractor.IR_FILE_PATTERN)
        files = sorted(glob.glob(pattern), key=os.path.getmtime)

        ir_files = []
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    filename = os.path.basename(filepath)
                    ir_files.append((filename, content))
            except IOError as e:
                pass

        return ir_files

    @staticmethod
    def parse_ir_stage_name(filename: str) -> str:
        if filename.startswith("pgx_lower_"):
            filename = filename[10:]

        if filename.endswith(".mlir"):
            filename = filename[:-5]

        parts = filename.rsplit('_', 2)
        if len(parts) >= 3:
            if (len(parts[-2]) == 8 and parts[-2].isdigit() and
                    len(parts[-1]) == 6 and parts[-1].isdigit()):
                return '_'.join(parts[:-2])

        return filename

    @staticmethod
    def extract_ir_stages() -> List[Dict[str, str]]:
        ir_files = IRExtractor.collect_ir_files()

        stages = []
        for filename, content in ir_files:
            stage_name = IRExtractor.parse_ir_stage_name(filename)
            stages.append({
                "stage": stage_name,
                "content": content,
                "filename": filename
            })

        return stages

    @staticmethod
    async def execute_with_ir_collection(
            query_executor,
            query: str,
            connection_obj
    ) -> Dict:
        IRExtractor.ensure_ir_directory()

        removed = IRExtractor.cleanup_all_ir_files()

        try:
            await connection_obj.execute("SET pgx_lower.log_enable = true;")
            await connection_obj.execute(
                "SET pgx_lower.enabled_categories = 'AST_TRANSLATE,RELALG_LOWER,DB_LOWER,JIT';"
            )

            results = await query_executor(query, connection_obj)

            await asyncio.sleep(0.1)

            ir_stages = IRExtractor.extract_ir_stages()

            return {
                "results": results,
                "ir_stages": ir_stages
            }

        finally:
            removed = IRExtractor.cleanup_all_ir_files()
