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
        with open(self.original_query_path, "w") as f:
            f.write(query)


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


    def hdd(self) -> str:
        with open(self.original_query_path, "r") as f:
            sql_query = f.read()
        assert self.executor.execute(sql_query)

        current_sql = sql_query

        for reduction_pass in range(10):  # HDD*
            logger.debug(f"Reduction pass #{reduction_pass + 1}")

            try:
                tree, tokens = self._parse(current_sql)
            except Exception:
                logger.error("Error parsing SQL")
                break

            depth = 1  # ignore root
            levels = self._bfs_levels(tree, max_depth=depth)
            progress = False

            while depth < len(levels):
                level_nodes = levels[depth]
                last_candidate: list[str] = [None]

                def test_fn(kept_nodes, _level_nodes=level_nodes, _tokens=tokens):
                    to_remove = [n for n in _level_nodes if n not in set(kept_nodes)]
                    try:
                        candidate = self._apply_removals(_tokens, to_remove)
                        self._parse(candidate)
                        result = self.executor.execute(candidate)
                        if result:
                            last_candidate[0] = candidate
                        return result
                    except Exception:
                        return False

                kept = self._ddmin(level_nodes, test_fn)

                logger.debug(f"Pass {reduction_pass + 1}, level {depth}: {len(level_nodes)} -> {len(kept)} nodes")

                if len(kept) < len(level_nodes):
                    current_sql = last_candidate[0]
                    self.save_query(current_sql)
                    progress = True
                    tree, tokens = self._parse(current_sql)

                depth += 1
                levels = self._bfs_levels(tree, depth)

            if not progress:
                break

        return current_sql