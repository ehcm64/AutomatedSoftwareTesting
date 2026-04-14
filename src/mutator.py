import sqlglot
from sqlglot import exp

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect

    def mutate_node(self, node: exp.Expr) -> exp.Expr:
        if isinstance(node, exp.Add):
            print(node)
            return exp.Sub(**node.args)
        return node

    def mutate(self, query: str) -> str:
        tree = sqlglot.parse_one(query, read=self.dialect)
        mutated_query: exp.Exp = tree.transform(self.mutate_node, copy=True)
        return mutated_query.sql(dialect=self.dialect)