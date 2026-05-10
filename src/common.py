from sqlglot import parse_one
import sqlglot.errors
import sqlglot.expressions as exp

def parse_query(query: str, dialect: str) -> exp.Expr | sqlglot.errors.ParseError:
    try:
        return parse_one(query, read=dialect)
    except sqlglot.errors.ParseError as e:
        return e