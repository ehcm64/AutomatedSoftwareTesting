from src.reducer import SQLReducer
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, required=True, help="path to the SQL query to minimize")
    parser.add_argument("--test", type=str, required=True, help="path to oracle shell script")
    args = parser.parse_args()

    reducer = SQLReducer(args.query, args.test)
    reducer.run()

if __name__ == "__main__":
    main()
