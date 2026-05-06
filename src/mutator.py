import sqlglot
import random
from sqlglot import exp
from loguru import logger
from .performance_statistics import timed
from typing import List, Tuple

MAX_NUMBER_OF_STATEMENTS = 15
PROBABILITY_OF_ADDING_STATEMENT = 0.0

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect
        self.schema: dict[str, list[str]] = {}
        self.query_id = None

    @timed("mutation")
    def mutate(self, query: str, query_id: str) -> Tuple[str, str]:
        """Main entrypoint for mutating a query. The mutation is performed in-place on the SQLGlot AST,
        which is won't modify the original string query. We will return both the mutated query and
        a short description of the mutation that was applied."""
        self.query_id = query_id
        query_parsed: exp.Expr = sqlglot.parse_one(query, read=self.dialect)
        if not isinstance(query_parsed, exp.Block):
            logger.warning(f"Expected a block of statements at the top level for query {query_id}")
            return (query, "None")
        block: exp.Block = query_parsed
        
        # We either mutate an existing statement or we add a new one.
        if len(block.expressions) < MAX_NUMBER_OF_STATEMENTS and random.random() < PROBABILITY_OF_ADDING_STATEMENT:
            # TODO: Derive the context from the previous statements and generate a new statement accordingly.
            index_to_add = random.randint(0, len(block.expressions))
            return (query, "None")
        else:
            index_to_mutate = random.randint(0, len(block.expressions) - 1)
            chosen_statement = block.expressions[index_to_mutate]
            context = block.expressions[:index_to_mutate]
            if isinstance(chosen_statement, exp.Select):
                mutation_description = self._mutate_select_statement(chosen_statement, context)
                return (block.sql(dialect=self.dialect), mutation_description)
            return (query, "None")

    def build_local_schema(self, context_statements: list[exp.Expr]) -> dict[str, list[str]]:
        local_schema = {}
        for statement in context_statements:
            if isinstance(statement, exp.Create):
                table = statement.find(exp.Table)
                assert table is not None, "Expected to find a table in the CREATE statement."
                table_name = table.name.lower()
                columns = []
                for column in statement.this.expressions:
                    if isinstance(column, exp.ColumnDef):
                        columns.append(column.this.name.lower())
                    if isinstance(column, exp.Identifier):
                        columns.append(column.name.lower())
                local_schema[table_name] = columns
        return local_schema

    ############################### SQL Clause Mutation Operators ###############################
    def _mutate_select_statement(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        available_mutations = [self._mutate_select_clause]
        if statement.args.get("joins") is not None:
            available_mutations.append(self._mutate_join_clause)
        if list(statement.find_all(exp.In, exp.Exists, exp.Any, exp.All)):
            available_mutations.append(self._mutate_subqeury_predicate)
        mutation_to_apply = random.choice(available_mutations)
        return mutation_to_apply(statement, context) 
    
    def _mutate_select_clause(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        is_distinct = statement.args.get("distinct")
        statement.set("distinct", exp.Distinct() if not is_distinct else None)
        return "Toggled DISTINCT in the SELECT clause."
    
    def _mutate_join_clause(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        joins = statement.args.get("joins")
        assert joins is not None, "Expected to have at least one join in order to mutate the join clause."

        # The join types are: INNER, LEFT, RIGHT, FULL, CROSS.
        # They are characterized by the pair (kind, side).
        types = [("CROSS", None), ("INNER", None), (None, "LEFT"), (None, "RIGHT"), (None, "FULL")]
        join_current = random.choice(joins)
        join_new_type = random.choice(types)
        join_current.set("kind", join_new_type[0])
        join_current.set("side", join_new_type[1])
        if join_new_type[0] == "CROSS":
            join_current.set("on", None)
        elif join_current.args.get("on") is None:
            local_schema = self.build_local_schema(context)
            assert local_schema, "Expected to have some tables in the local schema when adding a join condition."
            query_tables = [t.name.lower() for t in statement.find_all(exp.Table) if t.name]
            base_table_node = query_tables[0]
            base_table = base_table_node.lower()
            join_table = join_current.this.name.lower()
            if base_table not in local_schema or join_table not in local_schema\
                or not local_schema[base_table] or not local_schema[join_table]:
                logger.warning(f"Cannot add a join condition for tables {base_table} and {join_table}" +
                               f" for query {self.query_id} since they are not in the local schema or don't have columns.")
                return "None"
            base_col = local_schema[base_table][0]
            join_col = local_schema[join_table][0]
            condition_sql = f"{base_table}.{base_col} = {join_table}.{join_col}"
            join_current.set("using", None)
            join_current.set("on", exp.condition(condition_sql))
        return "Mutated a JOIN clause."
    
    def _mutate_subqeury_predicate(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        # The predicate can be of the following types:
        # - Type I: All, Any;
        # - Type II: In, Not In;
        # - Type III: Exists, Not Exists.
        targets = list(statement.find_all(exp.In, exp.Exists, exp.Any, exp.All))
        target = random.choice(targets)
        if isinstance(target, (exp.All, exp.Any)):
            new_class = exp.All if isinstance(target, exp.Any) else exp.Any
            target.replace(new_class(**target.args))
        elif isinstance(target, exp.Exists):
            if isinstance(target.parent, exp.Not):
                target.parent.replace(target.copy())
            else:
                target.replace(exp.Not(this=target.copy()))
        elif isinstance(target, exp.In):
            q = target.args.get("query")
            new_type = random.choice(["typeII", "typeIII"])
            if q is None:
                new_type = "typeII"
            if new_type == "typeII":
                if isinstance(target.parent, exp.Not):
                    target.parent.replace(target.copy())
                else:
                    target.replace(exp.Not(this=target.copy()))
            elif new_type == "typeIII":
                assert q is not None, "Expected to have a subquery for type III mutation."
                is_not_exists = random.choice([True, False])
                clean_q = q.unnest().copy()
                new_exists = exp.Exists(this=clean_q)
                if isinstance(target.parent, exp.Not):
                    target.parent.replace(exp.Not(this=new_exists) if is_not_exists else new_exists)
                else:
                    target.replace(exp.Not(this=new_exists) if is_not_exists else new_exists)
        return "Mutated a subquery predicate."