import sqlglot
from sqlglot import exp
from .performance_statistics import timed

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect

    def mutate_node(self, node: exp.Expr) -> exp.Expr:
        if isinstance(node, exp.Add):
            return exp.Sub(**node.args)
        return node
    
    @timed("mutation")
    def mutate(self, query: str) -> str:
        query_tree = sqlglot.parse_one(query, read=self.dialect)
        query_mutated: exp.Exp = query_tree.transform(self.mutate_node, copy=True)
        return query_mutated.sql(dialect=self.dialect)
