import os
from loguru import logger
import sqlglot
import sqlglot.errors
from sqlglot import exp
from .executor import SQLiteDifferentialExecutor, ExecutionResult
from .mutator import ASTMutator
from .logger import setup_logging

SQLITE_PATCHED_VERSION_PATH = "/usr/bin/sqlite3-3.39.4"
SQLITE_ORIGINAL_VERSION_PATH = "/usr/bin/sqlite3"
SEED_DIR = "./seeds"
SQL_DIALECT = "sqlite"

class SQLFuzzer:
    def __init__(self, seed_dir: str = SEED_DIR):
        self.seed_dir = seed_dir
        self.executor = SQLiteDifferentialExecutor(SQLITE_PATCHED_VERSION_PATH, SQLITE_ORIGINAL_VERSION_PATH)
        self.mutator = ASTMutator(dialect=SQL_DIALECT)
        self.pool: list[str] = []

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
        logger.info(f"Loaded {len(seeds)} seed files from {self.seed_dir}.")

        for (filename, query) in seeds.items():
            try:
                query_tree = sqlglot.parse_one(query, read=SQL_DIALECT)
                if isinstance(query_tree, exp.Block):
                    if any(isinstance(expr, exp.Command) for expr in query_tree.expressions):
                        logger.warning(
                            f"Failed to parse seed file {filename}: Contains statement with unsupported syntax, "
                            "and the parser fell back to parse it as a Command."
                        )
                        continue
                
                query_printed = query_tree.sql(dialect=SQL_DIALECT)
                result = self.executor.execute(query_printed)
                if result["status"] != "SUCCESS":
                    self.report_bug(result, query)
                    continue
                
                self.pool.append(query_printed)
            except sqlglot.errors.ParseError as e:
                logger.warning(f"Failed to parse seed file {filename}: {e.errors[0]}")
    
    def report_bug(self, result: ExecutionResult, query: str) -> None:
        logger.warning(f"Potential bug! Result: {result}, Query: \"{query}\"")

    def run(self) -> None:
        logging_dir = setup_logging()
        logger.info("Starting SQL Fuzzer.")
        logger.info(f"Logs will be saved to directory {logging_dir}.")
        self.load_seeds_into_pool()
        
        logger.info(f"Initial pool size: {len(self.pool)}.")
        for query in self.pool:
            mutated_query = self.mutator.mutate(query)
            result = self.executor.execute(mutated_query)
            if result["status"] != "SUCCESS":
                self.report_bug(result, mutated_query)