from loguru import logger
from .executor import OracleExecutor
from .logger import setup_logging
from .display import StatsDisplay
from .evaluation import token_count
import sqlglot

import logging
logging.getLogger("sqlglot").setLevel(logging.ERROR)

SQL_DIALECT = "sqlite"

class SQLReducer:
    def __init__(self, original_query_path: str, test_path: str):
        self.original_query_path = original_query_path
        self.test_path = test_path
        self.executor = OracleExecutor(self.test_path)


    def save_query(self, query: str) -> None:
        with open("query.sql", "w") as f:
            f.write(query)

        
    def hdd(self, sql_query: str, verbose: bool = True) -> str:
        self.save_query(sql_query)
        assert self.executor.execute()

        try:
            tree = sqlglot.parse_one(sql_query, read=SQL_DIALECT)
            logger.info("SQL parsed successfully")
        except Exception:
            logger.error("Error parsing SQL")
        
        return sql_query

    def run(self) -> None:
        with open(self.original_query_path, "r") as f:
            sql_query = f.read()
        
        reduced_query = self.hdd(sql_query)

        logger.info(f"Original query size: {token_count(self.original_query_path)} tokens")
        logger.info(f"Reduced query size: {token_count("query.sql")} tokens")
        logger.info(f"Compression ratio: {token_count(self.original_query_path) / token_count("query.sql")}")

        