from src.fuzzer import SQLFuzzer
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="command to execute", choices=["fuzz", "test"])
    parser.add_argument("--file", type=str, help="path to a file containing a single SQL query to test")
    args = parser.parse_args()
    
    fuzzer = SQLFuzzer()
    
    if args.command == "fuzz":
        fuzzer.run()
    elif args.command == "test" and args.file:
        with open(args.file, "r") as f:
            query = "".join(f.read().splitlines())
            result = fuzzer.executor.execute(query)
            fuzzer.report_bug(result, query)
    
if __name__ == "__main__":
    main()
