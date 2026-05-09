import subprocess
import os
from typing import TypedDict, Literal
from .performance_statistics import timed

class ExecutionResult(TypedDict):
    status: Literal["SUCCESS", "UNEXPECTED_ERROR", "LOGICAL_BUG", "CRASH", "INVALID", "TIMEOUT"]
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
            result_patched = subprocess.run(
                [self.db_executable_patched],
                input=query.encode("utf-8"),
                capture_output=True,
                timeout=10,
                env=self.patched_env
            )

            if result_original.returncode == 0 and result_patched.returncode == 0:
                original_output = result_original.stdout.decode("utf-8").strip()
                patched_output = result_patched.stdout.decode("utf-8").strip()
                # TODO: Handle sorted output or other non-determinism in results.
                if sorted(original_output) != sorted(patched_output):
                    return {"status": "LOGICAL_BUG",
                            "description": f"Patched output:\n{patched_output}\nOriginal output:\n{original_output}"}
                return {"status": "SUCCESS",
                        "description": f"Output:\n{patched_output}"}

            # Crash caused caused in the patched version by undefined behavior.
            if result_patched.returncode == 42:
                error_message = result_patched.stderr.decode("utf-8").strip()
                return {"status": "CRASH",
                        "description": f"ASAN/UBSAN Crash! Error: {error_message}"} 

            # If both version return an error with code 1, it's most likely an invalid query.
            # Invalid queries include syntax errors (parsing errors) or semantic errors
            # (e.g. referencing non-existent tables, violating a unique constraint).
            if result_patched.returncode == result_original.returncode and result_patched.returncode == 1:
                error_message_patched = result_patched.stderr.decode("utf-8").strip()
                error_message_original = result_original.stderr.decode("utf-8").strip()
                return {"status": "INVALID",
                        "description": f"Original error: {error_message_original}\nPatched error: {error_message_patched}"}
            
            # If we get here, we likely have an unexpected error in the patched version.
            # For example, the patched version might return an error code that shouldn't be triggeres
            # (e.g., referencing a non-existent table errors, but it is not the case).
            error_message_patched = result_patched.stderr.decode("utf-8").strip()
            error_message_original = result_original.stderr.decode("utf-8").strip()
            return {"status": "UNEXPECTED_ERROR",
                    "description": f"Original error: {error_message_original}\nPatched error: {error_message_patched}"}
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT",
                    "description": "Query execution timed out."}