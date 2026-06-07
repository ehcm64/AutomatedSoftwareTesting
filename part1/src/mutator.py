import random
import sqlglot.errors
import sqlglot.expressions as exp
from loguru import logger
from typing import List, Dict, Callable, Tuple
from .performance_statistics import timed
from .mutations.select import collect as collect_select_mutations
from .mutations.insert import collect as collect_insert_mutations
from .common import parse_query

MAX_NUMBER_OF_STATEMENTS = 15
PROBABILITY_OF_ADDING_STATEMENT = 0.0

Mutation = Tuple[Callable[[exp.Block], None], str]

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect
        self.mutation_cache = {}

    @timed("mutation")
    def mutate(self, query: str, query_id: str, num_mutations: int = 1) -> List[str]:
        """Main entrypoint for mutating a query. We are given the base query in the string format.
        We will parse it into an AST, and return up to `num_mutations` mutated versions of the query as strings."""
        query_parsed = parse_query(query, dialect=self.dialect)
        if isinstance(query_parsed, sqlglot.errors.ParseError):
            logger.warning(f"Failed to parse query {query_id} for mutation. Error: {query_parsed}.")
            return []
        if not isinstance(query_parsed, exp.Block):
            logger.warning(f"Expected a block of statements at the top level of the query.")
            return []
        
        # If we have already collected mutations for this query, we can just sample from the cache.
        # Otherwise, we first need to collect all available mutations by traversing the AST and applying our mutation rules.
        if query_id in self.mutation_cache:
            available_mutations = self.mutation_cache[query_id]
        else:
            available_mutations = self.collect_all_mutations(query_parsed)
            self.mutation_cache[query_id] = available_mutations
        
        # We then randomly sample from the available mutations and remove them from the cache.
        num_mutations = min(num_mutations, len(available_mutations))
        chosen_mutations_idx = random.sample(range(len(available_mutations)), num_mutations)
        chosen_mutations_idx.sort(reverse=True)
        chosen_mutations = [available_mutations.pop(i) for i in chosen_mutations_idx]
        results = []
        for mutation, _ in chosen_mutations:
            block_copy = query_parsed.copy()
            mutation(block_copy)
            results.append(block_copy.sql(dialect=self.dialect))
        return results

    def collect_all_mutations(self, block: exp.Block) -> List[Mutation]:
        schema: Dict[str, List[str]] = {}
        mutations: List[Mutation] = []
        for i, statement in enumerate(block.expressions):
            self.update_schema(statement, schema)
            if isinstance(statement, exp.Select):
                select_mutations = collect_select_mutations(statement, schema)
                mutations.extend([(lambda block, si=i, m=m: m(block.expressions[si]), f"[Statement {i}] {d}") for m, d in select_mutations])
            elif isinstance(statement, exp.Insert):
                insert_mutations = collect_insert_mutations(statement, schema)
                mutations.extend([(lambda block, si=i, m=m: m(block.expressions[si]), f"[Statement {i}] {d}") for m, d in insert_mutations])
        return mutations

    @staticmethod
    def update_schema(statement: exp.Expr, schema: Dict[str, List[str]]):
        if isinstance(statement, exp.Create) and isinstance(statement.this, exp.Schema) and isinstance(statement.this.this, exp.Table):
            table = statement.this.this
            if table is None:
                logger.warning(f"Expected to find a table in the CREATE statement of the query.")
                return
            table_name = table.name.lower()
            schema[table_name] = []
            for column in statement.this.expressions:
                if isinstance(column, exp.ColumnDef):
                    schema[table_name].append(column.this.name.lower())
                if isinstance(column, exp.Identifier):
                    schema[table_name].append(column.name.lower())