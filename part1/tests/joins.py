import sqlglot
import sqlglot.expressions as exp
from src.mutator import ASTMutator

def mutate_join():
    input_query = """
CREATE TABLE t1 (a, b, x);
CREATE TABLE t2 (c, d, y);
CREATE INDEX t1b ON t1(b);
CREATE INDEX t2d ON t2(d);
ANALYZE sqlite_master;
INSERT INTO sqlite_stat1 VALUES ('t1', 't1b', '10000 500');
INSERT INTO sqlite_stat1 VALUES ('t2', 't2d', '10000 500');
ANALYZE sqlite_master;
SELECT * FROM t1 CROSS JOIN t2 WHERE d = b;
SELECT * FROM t1 CROSS JOIN t2 WHERE d > b AND x = y;"""
    ASTMutator(dialect="sqlite").mutate(input_query, "567", 1)

def mutate_group_by():
    input_query = """
CREATE TABLE t1 (a, b, x);
INSERT INTO t1 VALUES (1, 2, 3), (1, 2, 4), (1, 3, 5), (2, 3, 6);
SELECT a, b, COUNT(*) FROM t1 GROUP BY a, b ORDER BY a;"""
    query_tree = sqlglot.parse_one(input_query, read="sqlite")
    ASTMutator(dialect="sqlite").mutate_group_by_clause(query_tree.find(exp.Select), query_tree.find(exp.Group))
if __name__ == "__main__":
    # mutate_join()
    mutate_group_by()