import os
from loguru import logger
import sqlglot
import sqlglot.errors
from sqlglot import exp
from sqlglot.errors import ErrorLevel
from .executor import SQLiteDifferentialExecutor, ExecutionResult
from .mutator import ASTMutator
from .logger import setup_logging

SQLITE_PATCHED_VERSION_PATH = "/usr/bin/sqlite3-3.39.4"
SQLITE_ORIGINAL_VERSION_PATH = "/usr/bin/sqlite3"
SEED_DIR = "./seeds"
SQL_DIALECT = "sqlite"

class SQLFuzzer:
    pool: list[str] = []

    def __init__(self, seed_dir: str = SEED_DIR):
        self.seed_dir = seed_dir
        self.executor = SQLiteDifferentialExecutor(SQLITE_PATCHED_VERSION_PATH, SQLITE_ORIGINAL_VERSION_PATH)
        self.mutator = ASTMutator(dialect=SQL_DIALECT)

    def load_seeds_into_pool(self) -> None:
        seeds: dict[str, str] = {}
        for filename in os.listdir(self.seed_dir):
            if filename.endswith('.sql'):
                with open(os.path.join(self.seed_dir, filename), 'r') as f:
                    seeds[filename] = f.read()
        if not seeds:
            logger.error(f"No seed files found in {self.seed_dir}.")
            raise FileNotFoundError(f"No seed files found in {self.seed_dir}.")
        logger.info(f"Loaded {len(seeds)} seed files from {self.seed_dir}.")

        for (filename, query) in seeds.items():
            try:
                query_parsed = sqlglot.parse_one(query, read=SQL_DIALECT)
                if isinstance(query_parsed, exp.Block):
                    if any(isinstance(expr, exp.Command) for expr in query_parsed.expressions):
                         logger.warning(f"Failed to parse seed file {filename}: Contains statement with unsupported syntax,\
                                        and the parser fall back to parse it as a Command.")
                         continue
                result = self.executor.execute(query)
                if result["status"] != "SUCCESS":
                    self.report_bug(result)
                else:
                    self.pool.append(query)
            except sqlglot.errors.ParseError as e:
                logger.warning(f"Failed to parse seed file {filename}: {e.errors[0]}")
    
    def report_bug(self, result: ExecutionResult) -> None:
        logger.warning(f"Bug found! {result}")

    def run(self) -> None:
        logging_dir = setup_logging()
        logger.info("Starting SQL Fuzzer.")
        logger.info(f"Logs will be saved to directoy {logging_dir}.")
        self.load_seeds_into_pool()
        
        logger.info(f"Initial pool size: {len(self.pool)}.")