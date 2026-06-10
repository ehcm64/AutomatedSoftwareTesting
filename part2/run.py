import argparse
from src.sqlglot_reducer import SQLQlotReducer
from src.antlr4_reducer import Antlr4Reducer
from src.treesitter_reducer import TreeSitterReducer
from src.evaluation import token_count
from loguru import logger

import logging
logging.getLogger("sqlglot").setLevel(logging.ERROR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, required=True, help="path to the SQL query to minimize")
    parser.add_argument("--test", type=str, required=True, help="path to oracle shell script")
    parser.add_argument("--parser", type=str, default="antlr4", choices=["sqlglot", "antlr4", "tree-sitter"], help="parser to use for reduction")
    args = parser.parse_args()
    original_query_path = args.query
    test_path = args.test
    parser_choice = args.parser

    with open(original_query_path, "r") as f:
        original_query = f.read()
    original_query_size = token_count(original_query_path)
    logger.info(f"Original query size: {original_query_size} tokens")
    logger.info(f"The reduced query will be saved to: {original_query_path}")

    if parser_choice == "sqlglot":
        reducer = SQLQlotReducer(original_query_path, test_path)
    elif parser_choice == "antlr4":
        reducer = Antlr4Reducer(original_query_path, test_path)
    elif parser_choice == "tree-sitter":
        reducer = TreeSitterReducer(original_query_path, test_path)
    else:
        raise ValueError(f"Unknown parser choice: {parser_choice}")
    reduced_query = reducer.hdd()
    reducer.save_query(reduced_query)
    assert reducer.executor.execute(reduced_query)
    reduced_query_size = token_count(original_query_path)
    logger.info(f"Reduced query size: {reduced_query_size} tokens")

    if reduced_query_size > original_query_size:
        logger.info(f"Reduction failed, query size increased: {reduced_query_size} > {original_query_size}")
        reducer.save_query(original_query)
        reduced_query_size = original_query_size

    token_reduction = (original_query_size - reduced_query_size) / original_query_size * 100
    logger.info(f"Token reduction: {token_reduction:.2f}%")


if __name__ == "__main__":
    main()
