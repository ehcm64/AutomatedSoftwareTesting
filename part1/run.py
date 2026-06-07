import argparse
from src.fuzzer import SQLFuzzer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="command to execute", choices=["fuzz", "test"])
    parser.add_argument("--file", type=str, help="path to a file containing a single SQL query to test")
    parser.add_argument("--queries", type=int, default=10000, help="number of queries to generate before stopping (default: 10000)")
    parser.add_argument("--seed", type=int, help="random seed for reproducibility (default: None)")
    args = parser.parse_args()
    
    fuzzer = SQLFuzzer()
    
    if args.command == "fuzz":
        fuzzer.run(max_queries=args.queries, seed=args.seed)
    elif args.command == "test" and args.file:
        with open(args.file, "r") as f:
            query = "".join(f.read().splitlines())
            result = fuzzer.executor.execute(query)
            fuzzer.report_execution_result(result, query, "None")

if __name__ == "__main__":
    main()
