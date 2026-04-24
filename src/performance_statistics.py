import time
from functools import wraps

# Global accumulators
timing_stats = {
    "mutation": 0.0,
    "execution": 0.0,
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


def get_performance_stats(num_queries: int) -> str:
    mutation_time = timing_stats["mutation"]
    execution_time = timing_stats["execution"]
    total_time = mutation_time + execution_time
    
    mutation_throughput = (num_queries / mutation_time) * 60 if mutation_time > 0 else 0
    overall_throughput = (num_queries / total_time) * 60 if total_time > 0 else 0
            
    return f"Performance stats: {num_queries} queries | {mutation_throughput:.2f} mutations/minute |{overall_throughput:.2f} runs/minute"
