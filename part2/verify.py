import subprocess, os, time

PARSER_CHOICE = "antlr4"


def verify():
    my_env = os.environ.copy()
    my_env["LOGURU_LEVEL"] = "INFO"
    input_output_dir = f"reductions/{PARSER_CHOICE}"

    subprocess.run(["mkdir", "-p", input_output_dir])
    for query in range(1, 21):
        print(f"QUERY {query}")
        input_file = f"{input_output_dir}/query_{query}.sql"
        sql_file = f"queries/query{query}/original_test.sql"
        oracle_file = f"queries/query{query}/test.sh"
        subprocess.run(["cp", sql_file, input_file])
        start_time = time.time()
        subprocess.run(["python3", "run.py", "--query", input_file, "--test", oracle_file, "--parser", PARSER_CHOICE], env=my_env)
        end_time = time.time()
        print(f"Time taken: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    verify()