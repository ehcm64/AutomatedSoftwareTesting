import sys
import time

NUM_LINES = 14
MIN_RENDER_INTERVAL = 0.1

class StatsDisplay:
    def __init__(self, max_queries: int):
        self.max_queries = max_queries
        self.corpus_size = 0
        self.queries_generated = 0
        self.successes = 0
        self.unexpected_errors = 0
        self.logical_bugs = 0
        self.crashes = 0
        self.invalids = 0
        self.timeouts = 0
        self.coverage = 0
        self._start_time = time.time()
        self._initialized = False
        self._last_render = 0.0

    def update(self, corpus_size: int, queries_generated: int, stats, coverage: int) -> None:
        self.corpus_size = corpus_size
        self.queries_generated = queries_generated
        self.successes = stats.successes
        self.unexpected_errors = stats.unexpected_errors
        self.logical_bugs = stats.logical_bugs
        self.crashes = stats.crashes
        self.invalids = stats.invalids
        self.timeouts = stats.timeouts
        self.coverage = coverage
        now = time.monotonic()
        if now - self._last_render >= MIN_RENDER_INTERVAL:
            self._render()
            self._last_render = now

    def _render(self) -> None:
        elapsed = time.time() - self._start_time
        throughput = (self.queries_generated / elapsed * 60) if elapsed > 0 else 0
        pct = (self.queries_generated / self.max_queries * 100) if self.max_queries > 0 else 0
        total = max(self.queries_generated, 1)

        lines = [
            "==============================================================",
            f"Progress:             {self.queries_generated:,} / {self.max_queries:,}  ({pct:.1f}%)",
            f"| Successes:          {self.successes:,}  ({self.successes / total * 100:.1f}%)",
            f"| Unexpected Errors:  {self.unexpected_errors:,}  ({self.unexpected_errors / total * 100:.1f}%)",
            f"| Logical Bugs:       {self.logical_bugs:,}  ({self.logical_bugs / total * 100:.1f}%)",
            f"| Crashes:            {self.crashes:,}  ({self.crashes / total * 100:.1f}%)",
            f"| Invalids:           {self.invalids:,}  ({self.invalids / total * 100:.1f}%)",
            f"| Timeouts:           {self.timeouts:,}  ({self.timeouts / total * 100:.1f}%)",
            f"Corpus:      {self.corpus_size}",
            f"Throughput:  {throughput:.0f} queries/min",
            f"Coverage:    {self.coverage:,} blocks",
            f"Elapsed:     {int(elapsed // 60)}m {int(elapsed % 60)}s",
            "==============================================================",
            "Press Ctrl+C to stop and see the final statistics."
        ]

        if self._initialized:
            sys.stdout.write(f"\033[{NUM_LINES}A")

        for line in lines:
            sys.stdout.write(f"\r\033[2K{line}\n")

        sys.stdout.flush()
        self._initialized = True

    def finish(self) -> None:
        self._render()
        sys.stdout.write("\n")
        sys.stdout.flush()