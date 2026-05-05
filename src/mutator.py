import sqlglot
import random
from sqlglot import exp
from loguru import logger
from .performance_statistics import timed

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect
        self.schema: dict[str, list[str]] = {}

    def update_schema(self, statement: exp.Create):
        table_name = statement.this.name.lower()
        if table_name in self.schema:
            return
        column_names = [column.name.lower() for column in statement.expressions]
        self.schema[table_name] = column_names

    @timed("mutation")
    def mutate(self, query: str) -> str:
        statements: exp.Expr = sqlglot.parse_one(query, read=self.dialect)
        if not isinstance(statements, exp.Block):
            logger.warning(f"Expected a block of statements at the top level for query \"{query}\"")
            return query
        
        self.schema.clear()
        expression_chosen = random.choice(statements.expressions)
        if isinstance(expression_chosen, exp.Create):
            self.mutate_create_statement(expression_chosen)
            self.update_schema(expression_chosen)
        elif isinstance(expression_chosen, exp.Insert):
            self.mutate_insert_statement(expression_chosen)
        elif isinstance(expression_chosen, exp.Select):
            self.mutate_select_statement(expression_chosen)
        return statements.sql(dialect=self.dialect)
    
    def mutate_create_statement(self, statement: exp.Create):
        pass
    
    def mutate_insert_statement(self, statement: exp.Insert):
        pass
    
    def mutate_select_statement(self, statement: exp.Select):
        clause_handlers = [self.mutate_where_clause]
        clause_handler_chosen = random.choice(clause_handlers)
        clause_handler_chosen(statement)
    
    def mutate_where_clause(self, statement: exp.Select):
        where_clause = statement.args.get("where")
        if where_clause is None:
            return
        for node in where_clause.find_all(exp.Add):
            node.replace(exp.Sub(**node.args))
