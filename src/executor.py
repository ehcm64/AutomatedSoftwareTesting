import subprocess
import os
from typing import TypedDict, Literal
from .performance_statistics import timed

class ExecutionResult(TypedDict):
    status: Literal["ORIGINAL_ERROR", "PATCHED_ERROR", "LOGICAL_BUG", "SUCCESS", "TIMEOUT"]
    description: str

class SQLiteDifferentialExecutor:
    def __init__(self, db_executable_patched: str, db_executable_original: str):
        self.db_executable_patched = db_executable_patched
        self.db_executable_original = db_executable_original
        
        # Set ASAN options to catch crashes while ignoring intentional compiler leaks,
        # and exit with code 42 to easily identify sanitizers crashes.
        self.patched_env = os.environ.copy()
        self.patched_env["ASAN_OPTIONS"] = "exitcode=42:detect_leaks=0"
    
    @timed("execution")
    def execute(self, query: str) -> ExecutionResult:
        try:
            result_original = subprocess.run(
                [self.db_executable_original],
                input=query.encode("utf-8"),
                capture_output=True,
                timeout=10
            )
            # Queries that cause errors in the original version should be investigated
            # (they are malformed or trigger unknown bugs).
            if result_original.returncode != 0:
                error_message = result_original.stderr.decode("utf-8")
                return {"status": "ORIGINAL_ERROR",
                        "description": f"Return code: {result_original.returncode}, Error: {error_message}"}
            
            result_patched = subprocess.run(
                [self.db_executable_patched],
                input=query.encode("utf-8"),
                capture_output=True,
                timeout=10,
                env=self.patched_env
            )
            # Here there's a defintely a bug since the original was fine (either crash or unexpected error).
            if result_patched.returncode == 42:
                error_message = result_patched.stderr.decode("utf-8")
                return {"status": "PATCHED_ERROR",
                        "description": f"ASAN/UBSAN CRASH! Error: {error_message}"}
            elif result_patched.returncode != 0:
                error_message = result_patched.stderr.decode("utf-8")
                return {"status": "PATCHED_ERROR",
                        "description": f"Return code: {result_patched.returncode}, Error: {error_message}"}
            if result_original.stdout.decode("utf-8") != result_patched.stdout.decode("utf-8"):
                patched_output = result_patched.stdout.decode("utf-8")
                original_output = result_original.stdout.decode("utf-8")
                return {"status": "LOGICAL_BUG",
                        "description": f"Patched output: {patched_output}, Original output: {original_output}"}
            output = result_patched.stdout.decode("utf-8")
            return {"status": "SUCCESS",
                    "description": f"Output: {output}"}
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT",
                    "description": "Query execution timed out."}
