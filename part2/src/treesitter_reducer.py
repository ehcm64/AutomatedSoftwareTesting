from loguru import logger
from .executor import OracleExecutor
from tree_sitter_language_pack import get_parser
import time


class TreeSitterReducer:
    def __init__(self, original_query_path: str, test_path: str):
        self.original_query_path = original_query_path
        self.test_path = test_path
        self.executor = OracleExecutor(self.test_path)
        self.ts_parser = get_parser("sql")


    def save_query(self, query: str) -> None:
        with open(self.original_query_path, "w") as f:
            f.write(query)


    def parse(self, sql: str):
        return self.ts_parser.parse(sql)


    def bfs_levels(self, root_node, max_depth: int) -> list[list]:
        levels = [[root_node]]
        current = [root_node]
        depth = 0
        while current and depth < max_depth:
            next_level = []
            for node in current:
                next_level.extend(
                    node.named_child(i) for i in range(node.named_child_count())
                )
            current = next_level
            levels.append(current)
            depth += 1
        return levels


    def reconstruct_sql(self, source: bytes, removed_ranges: list[tuple[int, int]]) -> str:
        if not removed_ranges:
            return source.decode("utf8")
        removed_ranges = sorted(set(removed_ranges))
        result = []
        pos = 0
        for start, end in removed_ranges:
            if start > pos:
                result.append(source[pos:start])
            pos = max(pos, end)
        result.append(source[pos:])
        return b"".join(result).decode("utf8").strip()


    def ddmin(self, elements, test_fn):
        granularity = 2
        while len(elements) >= 2:
            chunk_size = len(elements) // granularity
            chunks = [elements[i * chunk_size:(i + 1) * chunk_size]
                     for i in range(granularity)]
            chunks[-1] += elements[granularity * chunk_size:]  # append any leftover tail

            reduced = False
            for chunk in chunks:
                complement = [e for e in elements if e not in chunk]
                if test_fn(complement):
                    elements = complement
                    granularity = max(granularity - 1, 2)
                    reduced = True
                    break

            if not reduced:
                if granularity >= len(elements):
                    break
                granularity = min(granularity * 2, len(elements))

        return elements


    def hdd(self, reduction_passes: int = 10, min_reduction: float = 1.0, time_limit: float = 60.0) -> str:
        """
        Hierarchical Delta Debugging (HDD) implementation.
        Termination conditions:
        - If a reduction pass achieves less than `min_reduction` percent reduction, we stop.
        - If the total time taken exceeds `time_limit` seconds, we stop.
        - If we reach `reduction_passes` passes, we stop.
        """
        
        with open(self.original_query_path, "r") as f:
            sql_query = f.read()
        assert self.executor.execute(sql_query)

        current_sql = sql_query
        deadline = time.time() + time_limit
        test_count = 0
        test_errors = 0

        for reduction_pass in range(reduction_passes):
            logger.debug(f"Reduction pass #{reduction_pass + 1}")

            if time.time() >= deadline:
                logger.info(f"Termination: Reached time limit of {time_limit:.2f} seconds")
                return current_sql

            pass_start_size = len(current_sql)

            source = bytes(current_sql, "utf8")
            tree = self.parse(current_sql)
            root = tree.root_node()

            if root.has_error():
                logger.warning("Parse tree contains errors; attempting reduction anyway")

            depth = 1
            levels = self.bfs_levels(root, max_depth=depth)

            while depth < len(levels):
                if time.time() >= deadline:
                    logger.info(f"Termination: Reached time limit of {time_limit:.2f} seconds")
                    return current_sql

                level_nodes = levels[depth]

                node_ranges = [(n.start_byte(), n.end_byte()) for n in level_nodes]

                def test_fn(kept_ranges, _source=source, _node_ranges=node_ranges):
                    if time.time() >= deadline:
                        return False

                    nonlocal test_count, test_errors
                    test_count += 1

                    kept_set = set(kept_ranges)
                    removed = [(s, e) for (s, e) in _node_ranges if (s, e) not in kept_set]
                    candidate = self.reconstruct_sql(_source, removed)

                    try:
                        return self.executor.execute(candidate)
                    except Exception:
                        test_errors += 1
                        return False

                kept = self.ddmin(node_ranges, test_fn)
                kept_set = set(kept)

                logger.debug(f"Level {depth}: {test_count} tests total, {test_errors} errors")

                if len(kept) < len(node_ranges):
                    removed = [(s, e) for (s, e) in node_ranges if (s, e) not in kept_set]
                    current_sql = self.reconstruct_sql(source, removed)
                    self.save_query(current_sql)
                    source = bytes(current_sql, "utf8")
                    tree = self.parse(current_sql)
                    root = tree.root_node()

                depth += 1
                levels = self.bfs_levels(root, depth)


            pass_reduction = (pass_start_size - len(current_sql)) / pass_start_size * 100
            logger.debug(f"Pass {reduction_pass + 1} size reduction: {pass_reduction:.2f}%")

            if pass_reduction < min_reduction:
                logger.info(f"Termination: Reduction {pass_reduction:.2f}% is less than minimum {min_reduction:.2f}%")
                return current_sql

        logger.info(f"Termination: Reached maximum reduction passes of {reduction_passes}")
        return current_sql
