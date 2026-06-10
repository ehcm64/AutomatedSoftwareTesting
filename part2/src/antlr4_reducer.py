import time
from loguru import logger
from .executor import OracleExecutor
from .grammar.SQLiteLexer import SQLiteLexer
from .grammar.SQLiteParser import SQLiteParser
from antlr4 import CommonTokenStream, InputStream, TerminalNode
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from antlr4.error.ErrorListener import ErrorListener


class ThrowingErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise SyntaxError(f"line {line}:{column} {msg}")


class Antlr4Reducer:
    def __init__(self, original_query_path: str, test_path: str):
        self.original_query_path = original_query_path
        self.test_path = test_path
        self.executor = OracleExecutor(self.test_path)


    def save_query(self, query: str) -> None:
        """Persist the final and the intermediate reduced queries to the same file as required."""
        with open(self.original_query_path, "w") as f:
            f.write(query)


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

        for reduction_pass in range(reduction_passes):
            logger.debug(f"Reduction pass {reduction_pass + 1}")

            if time.time() >= deadline:
                logger.info(f"Termination: Reached time limit of {time_limit:.2f} seconds")
                return current_sql

            pass_start_size = len(current_sql)

            # Depth 1: At the highest level, we split at the statement level.
            # ANTLR4 grammar has some problems to enumerate all statements (e.g., query 7),
            # so we parse based on the semicolon token, which proved to be enough.
            stmts = [s.strip() for s in current_sql.split(';') if s.strip()]
            last_d1: list[str] = [None]

            def test_stmts(kept_stmts):
                if time.time() >= deadline:
                    return False
                candidate = ';\n'.join(kept_stmts) + ';'
                result = self.executor.execute(candidate)
                if result:
                    last_d1[0] = candidate
                return result

            kept_stmts = self._ddmin(stmts, test_stmts)
            logger.debug(f"Pass {reduction_pass + 1}, depth 1: {len(stmts)} -> {len(kept_stmts)} stmts")

            if len(kept_stmts) < len(stmts):
                current_sql = last_d1[0]
                self.save_query(current_sql)

            if time.time() >= deadline:
                logger.info(f"Termination: Reached time limit of {time_limit:.2f} seconds")
                return current_sql

            # Depth >=2: From depth 2 downwards, we rely on the ANTLR4 parse tree.
            try:
                tree, tokens = self._parse(current_sql)
            except Exception:
                logger.error("Error parsing SQL")
                return current_sql

            depth = 2
            levels = self._bfs_levels(tree, max_depth=depth)

            while depth < len(levels):
                if time.time() >= deadline:
                    logger.info(f"Termination: Reached time limit of {time_limit:.2f} seconds")
                    return current_sql

                level_nodes = levels[depth]
                last_d2: list[str] = [None]

                def test_fn(kept_nodes, _level_nodes=level_nodes, _tokens=tokens):
                    if time.time() >= deadline:
                        return False
                    to_remove = [n for n in _level_nodes if n not in set(kept_nodes)]
                    try:
                        candidate = self._apply_removals(_tokens, to_remove)
                        self._parse(candidate)
                        result = self.executor.execute(candidate)
                        if result:
                            last_d2[0] = candidate
                        return result
                    except Exception:
                        return False

                kept = self._ddmin(level_nodes, test_fn)

                logger.debug(f"Pass {reduction_pass + 1}, depth {depth}: {len(level_nodes)} -> {len(kept)} nodes")

                if len(kept) < len(level_nodes):
                    current_sql = last_d2[0]
                    self.save_query(current_sql)
                    tree, tokens = self._parse(current_sql)

                depth += 1
                levels = self._bfs_levels(tree, depth)

            pass_reduction = (pass_start_size - len(current_sql)) / pass_start_size * 100
            logger.debug(f"Pass {reduction_pass + 1} size reduction: {pass_reduction:.2f}%")

            if pass_reduction < min_reduction:
                logger.info(f"Termination: Reduction {pass_reduction:.2f}% is less than minimum {min_reduction:.2f}%")
                return current_sql
        logger.info(f"Termination: Reached maximum reduction passes of {reduction_passes}")
        return current_sql


    def _parse(self, sql: str):
        stream = InputStream(sql)
        lexer = SQLiteLexer(stream)
        lexer.removeErrorListeners()
        tokens = CommonTokenStream(lexer)
        parser = SQLiteParser(tokens)
        parser.removeErrorListeners()
        parser.addErrorListener(ThrowingErrorListener())
        tree = parser.sql_stmt_list()
        return tree, tokens


    def _bfs_levels(self, tree, max_depth: int) -> list[list]:
        levels, current = [[tree]], [tree]
        depth = 0
        while current and depth < max_depth:
            next_level = []
            for node in current:
                for i in range(node.getChildCount()):
                    child = node.getChild(i)
                    if not isinstance(child, TerminalNode):
                        next_level.append(child)
            current = next_level
            levels.append(current)
            depth += 1
        return levels


    def _delete_adjacent_separator(self, rewriter: TokenStreamRewriter, node, deleted_indices: set) -> None:
        parent = node.parentCtx
        if parent is None:
            return
        siblings = [parent.getChild(i) for i in range(parent.getChildCount())]
        try:
            idx = next(i for i, s in enumerate(siblings) if s is node)
        except StopIteration:
            return
        for candidate_idx in (idx + 1, idx - 1):
            if 0 <= candidate_idx < len(siblings):
                sib = siblings[candidate_idx]
                if isinstance(sib, TerminalNode) and sib.getText() in (',', ';'):
                    tok_idx = sib.symbol.tokenIndex
                    if tok_idx not in deleted_indices:
                        rewriter.delete(
                            rewriter.DEFAULT_PROGRAM_NAME,
                            tok_idx,
                            tok_idx,
                        )
                        deleted_indices.add(tok_idx)
                    return


    def _apply_removals(self, tokens: CommonTokenStream, nodes: list) -> str:
        rewriter = TokenStreamRewriter(tokens)
        deleted_separator_indices: set = set()
        for node in nodes:
            rewriter.delete(
                rewriter.DEFAULT_PROGRAM_NAME,
                node.start.tokenIndex,
                node.stop.tokenIndex,
            )
            self._delete_adjacent_separator(rewriter, node, deleted_separator_indices)
        result = rewriter.getDefaultText()
        return '\n'.join(line for line in result.splitlines() if line.strip())


    def _ddmin(self, elements, test_fn):
        granularity = 2
        while len(elements) >= 2:
            chunk_size = len(elements) // granularity
            chunks = [elements[i * chunk_size:(i + 1) * chunk_size]
                      for i in range(granularity)]
            chunks[-1] += elements[granularity * chunk_size:]

            reduced = False
            for chunk in chunks:
                chunk_set = set(chunk)
                complement = [e for e in elements if e not in chunk_set]
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