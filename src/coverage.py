import os
import struct
import subprocess
from loguru import logger

class FastCoverageTracker:
    """
    A fast, heuristic-based coverage tracker inspired by AFL++ that reads .gcda files directly.
    Instead of invoking the slow `gcov` binary during the fuzzing loop, we
    directly read the binary .gcda file. In a .gcda file, counters are 64-bit
    integers. If any 64-bit block that was previously 0 becomes > 0, we know
    we've hit new coverage (a new basic block).
    """
    def __init__(self, gcda_path: str):
        self.gcda_path = gcda_path
        self.previous_gcda_state = {}
        self.global_buckets = {}

    def get_bucket(self, count: int) -> int:
        if count <= 0: return 0
        if count == 1: return 1
        if count == 2: return 2
        if count == 3: return 3
        if count <= 7: return 4
        if count <= 15: return 5
        if count <= 31: return 6
        if count <= 127: return 7
        return 8

    def check_for_new_coverage(self) -> bool:
        if not os.path.exists(self.gcda_path):
            return False
            
        new_coverage = False
        with open(self.gcda_path, 'rb') as f:
            data = f.read()
            
            # A .gcda file has a 12-byte header (magic, version, stamp)
            for i in range(12, len(data) - 7, 8):
                val = struct.unpack('<Q', data[i:i+8])[0]
                
                # Calculate hits for this specific query
                hits = val - self.previous_gcda_state.get(i, 0)
                
                if hits > 0:
                    bucket = self.get_bucket(hits)
                    
                    # If we haven't seen this offset, or reached a higher bucket
                    if i not in self.global_buckets or bucket > self.global_buckets[i]:
                        self.global_buckets[i] = bucket
                        new_coverage = True
                
                # Update the state for the next query
                self.previous_gcda_state[i] = val
                    
        return new_coverage

    def get_coverage_count(self) -> int:
        return len(self.global_buckets)

def run_final_lcov_evaluation(source_dir: str):
    """
    Runs the official `lcov` tool to generate the Line, Branch, and Function
    coverage report for the final evaluation.
    """
    logger.bind(terminal=True).info(f"Running final lcov evaluation in {source_dir}...")
    
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
        
    logger.bind(terminal=True).info("Final lcov coverage report:")
    for line in summary_result.stdout.split('\n'):
        if line.strip():
            logger.bind(terminal=True).info(line.strip())
