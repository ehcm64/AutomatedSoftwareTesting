from loguru import logger
from .executor import OracleExecutor
from sqlglot import exp, parse_one

SQL_DIALECT = "sqlite"


class SQLGlotReducer:
    def __init__(self, original_query_path: str, test_path: str):
        self.original_query_path = original_query_path
        self.test_path = test_path
        self.executor = OracleExecutor(self.test_path)


    def save_query(self, query: str) -> None:
        with open(self.original_query_path, "w") as f:
            f.write(query)


    def bfs_levels(self, tree: exp.Expr, max_depth: int) -> list[list[exp.Expr]]:
        levels, current = [[tree]], [tree]
        depth = 0
        while current and depth < max_depth:
            next_level = []
            for node in current:
                for child in node.args.values():
                    if isinstance(child, exp.Expr):
                        next_level.append(child)
                    elif isinstance(child, list):
                        next_level.extend(c for c in child if isinstance(c, exp.Expr))
            current = next_level
            levels.append(current)
            depth += 1
        return levels


    def remove_node(self, node: exp.Expr) -> None:
        parent = node.parent
        if parent is None:
            return
        for key, val in parent.args.items():
            if isinstance(val, list) and node in val:
                val.remove(node)
                node.parent = None
                return
            elif val is node:
                parent.args[key] = None
                node.parent = None
                return
                

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

        
    def hdd(self) -> str:
        with open(self.original_query_path, "r") as f:
            sql_query = f.read()
        assert self.executor.execute(sql_query)

        current_sql = sql_query
        test_count = 0
        test_errors = 0

        for reduction_pass in range(10): # HDD*
            logger.debug(f"Reduction pass #{reduction_pass + 1}")

            try:
                tree = parse_one(current_sql, read=SQL_DIALECT)
                logger.debug("SQL parsed successfully")
            except Exception:
                logger.error("Error parsing SQL")
                break

            depth = 1 # ignore root of tree
            levels = self.bfs_levels(tree, max_depth=depth)
            progress = False
    
            while depth < len(levels):
                level_nodes = levels[depth]
    
                node_sqls = [n.sql() for n in level_nodes]
    
                def test_fn(kept_sqls):
                    nonlocal test_count
                    test_count += 1

                    try:
                        t = parse_one(current_sql, dialect=SQL_DIALECT)
                        test_levels = self.bfs_levels(t, max_depth=depth)
                    except Exception:
                        logger.error(f"Error parsing SQL in test_fn")
                        return False
                    if depth >= len(test_levels):
                        logger.error(f"Error: depth {depth} >= len(test_levels) {len(test_levels)}")
                        return False
    
                    kept_set = set(kept_sqls)
                    for node in test_levels[depth]:
                        if node.sql() not in kept_set:
                            self.remove_node(node)
    
                    try:
                        candidate = t.sql(pretty=False) # fails sometimes...
                        parse_one(candidate, dialect=SQL_DIALECT) # sanity check, also fails even more often...
                        return self.executor.execute(candidate)
                    except Exception:
                        nonlocal test_errors
                        test_errors += 1
                        return False
    
                kept     = self.ddmin(node_sqls, test_fn)
                kept_set = set(kept)

                logger.debug(f"Level {depth}: Generated {test_count} test cases, including {test_errors} errors")
    
                if len(kept) < len(node_sqls): # prune the nodes on current level and update the tree and sql
                    for node in levels[depth]:
                        if node.sql() not in kept_set:
                            self.remove_node(node)

                    current_sql = tree.sql(pretty=False)
                    self.save_query(current_sql)  # persist intermediate reduction
                    progress = True
                    tree = parse_one(current_sql, dialect=SQL_DIALECT)
                
                depth += 1
                levels = self.bfs_levels(tree, depth) # add next level of the tree
    
            if not progress:
                break

        return current_sql    
