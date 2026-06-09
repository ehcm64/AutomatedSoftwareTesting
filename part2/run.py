import argparse
from src.sqlglot_reducer import SQLQlotReducer as SQLReducer
from src.evaluation import token_count
from loguru import logger

import logging
logging.getLogger("sqlglot").setLevel(logging.ERROR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, required=True, help="path to the SQL query to minimize")
    parser.add_argument("--test", type=str, required=True, help="path to oracle shell script")
    args = parser.parse_args()
    original_query_path = args.query
    test_path = args.test

    with open(original_query_path, "r") as f:
        original_query = f.read()
    original_query_size = token_count(original_query_path)
    logger.info(f"Original query size: {original_query_size} tokens")
    logger.info(f"The reduced query will be saved to: {original_query_path}")

    reducer = SQLReducer(original_query_path, test_path)
    reduced_query = reducer.hdd()
    reducer.save_query(reduced_query)
    assert reducer.executor.execute(reduced_query)
    reduced_query_size = token_count(original_query_path)
    logger.info(f"Reduced query size: {reduced_query_size} tokens")

    if reduced_query_size > original_query_size:
        logger.info(f"Reduction failed, query size increased: {reduced_query_size} > {original_query_size}")
        reducer.save_query(original_query)
        reduced_query_size = original_query_size

    compression_ratio = original_query_size / reduced_query_size
    logger.info(f"Compression ratio: {compression_ratio}")


if __name__ == "__main__":
    main()