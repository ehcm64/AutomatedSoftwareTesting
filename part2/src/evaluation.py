import sqlglot


def token_count(query_path: str) -> int:
    with open(query_path, "r") as f:
        query = f.read()
        tokenizer = sqlglot.Tokenizer()
        tokens = tokenizer.tokenize(query)
        return len(tokens)