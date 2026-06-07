import subprocess

class OracleExecutor:
    # Runs the oracle script and returns True if bug is still present, False otherwise.

    def __init__(self, oracle_script: str):
        self.oracle_script = oracle_script
        
    def execute(self) -> bool:
        try:
            result = subprocess.run(
                [self.oracle_script],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return True
            return False

        except subprocess.TimeoutExpired:
            return False
