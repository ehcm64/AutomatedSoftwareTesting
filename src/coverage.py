import os
import struct
import subprocess
from loguru import logger

class FastCoverageTracker:
    """
    A fast, heuristic-based coverage tracker that reads .gcda files directly.
    Instead of invoking the slow `gcov` binary during the fuzzing loop, we
    directly read the binary .gcda file. In a .gcda file, counters are 64-bit
    integers. If any 64-bit block that was previously 0 becomes > 0, we know
    we've hit new coverage (a new basic block).
    """
    def __init__(self, gcda_path: str):
        self.gcda_path = gcda_path
        self.known_non_zero_offsets = set()

    def check_for_new_coverage(self) -> bool:
        if not os.path.exists(self.gcda_path):
            return False
            
        new_coverage = False
        with open(self.gcda_path, 'rb') as f:
            data = f.read()
            
            # A .gcda file has a 12-byte header (magic, version, stamp)
            # We can safely scan the rest of the file in 8-byte chunks.
            # Tags and lengths are 32-bit, but they are static for a given compilation.
            # Only the 64-bit counters change. If a previously 0 value becomes > 0,
            # we have discovered a new path!
            for i in range(12, len(data) - 7, 8):
                val = struct.unpack('<Q', data[i:i+8])[0]
                if val > 0 and i not in self.known_non_zero_offsets:
                    self.known_non_zero_offsets.add(i)
                    new_coverage = True
                    
        return new_coverage

    def get_coverage_count(self) -> int:
        return len(self.known_non_zero_offsets)

def run_final_lcov_evaluation(source_dir: str):
    """
    Runs the official `lcov` tool to generate the Line, Branch, and Function
    coverage report for the final evaluation.
    """
    logger.info(f"Running final lcov evaluation in {source_dir}...")
    
    # 1. Capture coverage data
    capture_result = subprocess.run(
        ["lcov", "--capture", "--directory", ".", "--output-file", "cov.info", "--rc", "lcov_branch_coverage=1"],
        cwd=source_dir,
        capture_output=True,
        text=True
    )
    
    if capture_result.returncode != 0:
        logger.error(f"lcov --capture failed with return code {capture_result.returncode}")
        logger.error(capture_result.stderr)
        return
        
    # 2. Print summary
    summary_result = subprocess.run(
        ["lcov", "--summary", "cov.info", "--rc", "lcov_branch_coverage=1"],
        cwd=source_dir,
        capture_output=True,
        text=True
    )
    
    if summary_result.returncode != 0:
        logger.error(f"lcov --summary failed with return code {summary_result.returncode}")
        logger.error(summary_result.stderr)
        return
        
    logger.info("Final lcov coverage report:")
    for line in summary_result.stdout.split('\n'):
        if line.strip():
            logger.info(line.strip())
