import time
from functools import wraps

# Global accumulators
timing_stats = {
    "mutation": 0.0
}

def timed(category: str):
    """Accumulates elapsed time into timing_stats[category]."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            timing_stats[category] += time.perf_counter() - start
            return result
        return wrapper
    return decorator

def get_generation_throughput(num_queries: int) -> float:
    mutation_time = timing_stats["mutation"]
    mutation_throughput = (num_queries / mutation_time) * 60 if mutation_time > 0 else 0
    return mutation_throughput
