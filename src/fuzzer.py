import os
from loguru import logger
import sqlglot
import sqlglot.errors
from sqlglot import exp
from .executor import SQLiteDifferentialExecutor, ExecutionResult
from .mutator import ASTMutator
from .logger import setup_logging
from .performance_statistics import get_performance_stats
from .query_statistics import QueryStatistics

SQLITE_PATCHED_VERSION_PATH = "/usr/bin/sqlite3-3.39.4"
SQLITE_ORIGINAL_VERSION_PATH = "/usr/bin/sqlite3"
SEED_DIR = "./seeds"
SQL_DIALECT = "sqlite"

class SQLFuzzer:
    def __init__(self, seed_dir: str = SEED_DIR):
        self.seed_dir = seed_dir
        self.executor = SQLiteDifferentialExecutor(SQLITE_PATCHED_VERSION_PATH, SQLITE_ORIGINAL_VERSION_PATH)
        self.mutator = ASTMutator(dialect=SQL_DIALECT)
        self.pool_list: list[tuple[str, str]] = []
        self.pool_set: set[str] = set()
        self.statistics = QueryStatistics()

    def load_seeds_into_pool(self) -> None:
        """
        Load and validate the seed file. The parser provided by `sqlglot` doesn't cover the entire dialect of SQLite.
        For now, we want to start with a clean pool, so we consider only the test cases with:
            (i) no parsing errors;
            (ii) no parsing warning (unsupported syntax to falls down to the generic Command);
            (iii) success execution after doing a parse + print cycle.
        """
        seeds: dict[str, str] = {}
        for filename in os.listdir(self.seed_dir):
            if filename.endswith('.sql'):
                with open(os.path.join(self.seed_dir, filename), 'r') as f:
                    seeds[filename] = "".join(f.read().splitlines())
        if not seeds:
            logger.error(f"No seed files found in {self.seed_dir}.")
            raise FileNotFoundError(f"No seed files found in {self.seed_dir}.")
        logger.info(f"Loading and validating {len(seeds)} seed files from {self.seed_dir}.")

        for (filename, query) in seeds.items():
            try:
                result_initial = self.executor.execute(query)
                if result_initial["status"] != "SUCCESS":
                    self.report_execution_result(result_initial, query)
                    continue

                query_tree = sqlglot.parse_one(query, read=SQL_DIALECT)
                if isinstance(query_tree, exp.Block):
                    if any(isinstance(expr, exp.Command) for expr in query_tree.expressions):
                        logger.warning(
                            f"Failed to parse seed file {filename}: Contains statement with unsupported syntax, "
                            "and the parser fell back to parse it as a Command."
                        )
                        continue
                
                query_printed = query_tree.sql(dialect=SQL_DIALECT)
                result_after = self.executor.execute(query_printed)
                if result_after["status"] != "SUCCESS":
                    self.report_execution_result(result_after, query_printed)
                    continue
                
                self.report_query(query_printed, id=filename, parent="None")
                self.pool_list.append((query_printed, filename))
                self.pool_set.add(query_printed)
            except sqlglot.errors.ParseError as e:
                logger.warning(f"Failed to parse seed file {filename}: {e.errors[0]}")
    
    def pretty_print(self, query: str) -> str:
        query_parsed = sqlglot.parse_one(query, read=SQL_DIALECT)
        if isinstance(query_parsed, exp.Block):
            return ";\n".join(expr.sql(dialect=SQL_DIALECT) for expr in query_parsed.expressions) + ";"
        return query_parsed.sql(dialect=SQL_DIALECT)

    def report_query(self, query: str, id: str, parent: str) -> None:
        """Helpful to keep track of the mutation tree and the queries that are being executed."""
        logger.bind(query=True).info(f"--- index: {id}; parent: {parent}\n{self.pretty_print(query)}")

    def report_execution_result(self, result: ExecutionResult, query: str) -> None:
        pretty_output = "\n".join([
            f"Execution result with status {result['status']}!",
            f"Description:\n{result['description']}",
            f"Query:\n{self.pretty_print(query)}"
        ])
        if result["status"] != "SUCCESS":
            logger.error(pretty_output)
        else:
            logger.info(pretty_output)

    def run(self) -> None:
        logging_dir = setup_logging()
        logger.info("Starting SQL Fuzzer.")
        logger.info(f"Logs will be saved to directory {logging_dir}.")
        self.load_seeds_into_pool()

        logger.info(f"Starting mutations with initial pool size: {len(self.pool_list)}.")
        generated = 0
        while True:
            if generated > 1e5 or len(self.pool_list) == 0:
                break
            current_query, current_index = self.pool_list.pop()
            for _ in range(10):
                mutated_query = self.mutator.mutate(current_query)

                if mutated_query in self.pool_set:
                    continue
                generated += 1
                self.report_query(mutated_query, id=str(generated), parent=current_index)

                result = self.executor.execute(mutated_query)
                self.statistics.collect(result)
                if result["status"] != "SUCCESS":
                    self.report_execution_result(result, mutated_query)
                else:
                    self.pool_list.append((mutated_query, str(generated)))
                    self.pool_set.add(mutated_query)
            if len(self.pool_set) % 100 == 0:
                logger.info(len(self.pool_set))
        logger.info(f"Finished trying {len(self.pool_set)} queries.")
        logger.info(get_performance_stats(self.statistics.total_queries))
        logger.info(self.statistics.get_validity_stats())
        logger.info(self.statistics.get_top30_keywords_stats(list(self.pool_set)))