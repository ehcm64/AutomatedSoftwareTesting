import sqlglot
import random
from sqlglot import exp
from loguru import logger
from .performance_statistics import timed
from typing import List, Tuple, Callable

MAX_NUMBER_OF_STATEMENTS = 15
PROBABILITY_OF_ADDING_STATEMENT = 0.0

class ASTMutator:
    def __init__(self, dialect: str):
        self.dialect = dialect
        self.schema: dict[str, list[str]] = {}
        self.mutation_cache = {}
        self.query_id = None

    @timed("mutation")
    def mutate(self, query: str, query_id: str, num_mutations: int = 1) -> List[str]:
        """Main entrypoint for mutating a query. We are given the base query in the string format.
        We will parse it into an AST, and return up to `num_mutations` mutated versions of the query as strings."""
        query_parsed: exp.Expr = sqlglot.parse_one(query, read=self.dialect)
        if not isinstance(query_parsed, exp.Block):
            logger.warning(f"Expected a block of statements at the top level for query {query_id}")
            return []
        
        # If we have already collected mutations for this query, we can just sample from the cache.
        # Otherwise, we first need to collect all available mutations by traversing the AST and applying our mutation rules.
        if query_id in self.mutation_cache:
            available_mutations = self.mutation_cache[query_id]
        else:
            available_mutations = self.collect_all_mutations(query_parsed, query_id)
            self.mutation_cache[query_id] = available_mutations
        
        # We then randomly sample from the available mutations and remove them from the cache.
        num_mutations = min(num_mutations, len(available_mutations))
        chosen_mutations_idx = random.sample(range(len(available_mutations)), num_mutations)
        chosen_mutations_idx.sort(reverse=True)
        chosen_mutations = [available_mutations.pop(i) for i in chosen_mutations_idx]
        results = []
        for mutation, _ in chosen_mutations:
            block_copy = sqlglot.parse_one(query, read=self.dialect)
            assert isinstance(block_copy, exp.Block), f"Expected a block of statements at the top level for query {query_id}"
            mutation(block_copy)
            results.append(block_copy.sql(dialect=self.dialect))
        return results

    def collect_all_mutations(self, block: exp.Block, query_id: str) -> List[Tuple[Callable[[exp.Block], None], str]]:
        self.schema = {}
        self.query_id = query_id
        available_mutations: List[Tuple[Callable[[exp.Block], None], str]] = []
        for i, statement in enumerate(block.expressions):
            self.update_schema(statement, query_id)
            if isinstance(statement, exp.Select):
                # Mutation 1: Toggle DISTINCT in the SELECT clause.
                available_mutations.extend(self.collect_mutations_select_clause(i))

                # Mutation 2: Mutate the JOIN clause (change type, add/remove conditions).
                # The join types are: INNER, LEFT, RIGHT, FULL, CROSS.
                # They are characterized by the pair (kind, side).
                available_mutations.extend(self.collect_mutations_join_clause(statement, i))

                # Mutation 3: Mutate subquery predicates (EXISTS, IN, ANY, ALL).
                # There are several types of such predicates:
                # Type I: [ANY, ALL];
                # Type II: [IN, NOT IN];
                # Type III: [EXISTS, NOT EXISTS].
                available_mutations.extend(self.collect_mutations_subquery_predicate(statement, i))

                # Mutation 4: Remove expressions from the GROUP BY clause.
                available_mutations.extend(self.collect_mutations_group_by_clause(statement, i))

                # Mutation 5: Mutate aggregate functions (change function, add/remove DISTINCT).
                available_mutations.extend(self.collect_mutations_aggregate_function(statement, i))

                # # Mutation 6: Replace a relational operator (=, <>, <, <=, >, >=).
                available_mutations.extend(self.collect_mutations_relational_operator(statement, i))

                # Mutation 7: Replace a logical operator (AND, OR).
                available_mutations.extend(self.collect_mutations_logical_operator(statement, i))

                # Mutation 8: Insert a unary operator (+1, -1, negate) on an arithmetic expression.
                available_mutations.extend(self.collect_mutations_unary_operator(statement, i))

                # Mutation 9: Wrap an arithmetic expression in ABS or -ABS.
                available_mutations.extend(self.collect_mutations_absolute_value(statement, i))

                # Mutation 10: Replace an arithmetic operator (+, -, *, /, %).
                available_mutations.extend(self.collect_mutations_arithmetic_operator(statement, i))

                # Mutation 11: Replace BETWEEN with explicit inequalities.
                available_mutations.extend(self.collect_mutations_between(statement, i))

                # Mutation 12: Mutate a LIKE/ILIKE wildcard pattern.
                available_mutations.extend(self.collect_mutations_like_patterns(statement, i))
        return available_mutations

    def update_schema(self, statement: exp.Expr, query_id: str):
        if isinstance(statement, exp.Create) and isinstance(statement.this, exp.Schema) and isinstance(statement.this.this, exp.Table):
            table = statement.this.this
            if table is None:
                logger.warning(f"Expected to find a table in the CREATE statement for query {query_id}")
                return
            table_name = table.name.lower()
            self.schema[table_name] = []
            for column in statement.this.expressions:
                if isinstance(column, exp.ColumnDef):
                    self.schema[table_name].append(column.this.name.lower())
                if isinstance(column, exp.Identifier):
                    self.schema[table_name].append(column.name.lower())

    ############################### SQL Clause Mutation Operators ###############################    
    def collect_mutations_select_clause(self, statement_index: int):
        desc = f"[Statement {statement_index}] Toggle DISTINCT in SELECT clause."
        return [(lambda block: self.mutate_select_clause(statement=block.expressions[statement_index]), desc)]

    def mutate_select_clause(self, statement: exp.Select):
        is_distinct = statement.args.get("distinct")
        statement.set("distinct", exp.Distinct() if not is_distinct else None)
    
    def collect_mutations_join_clause(self, statement: exp.Select, statement_index: int):
        join_types = [("CROSS", None), ("INNER", None), (None, "LEFT"), (None, "RIGHT"), (None, "FULL")]
        joins = statement.args.get("joins", [])
        mutations = []
        for join_idx, join_target in enumerate(joins):
            join_target_type = (join_target.args.get("kind"), join_target.args.get("side"))
            join_target_type_str = join_target.args.get("kind") or join_target.args.get("side")
            possible_new_join_types = [jt for jt in join_types if jt != join_target_type]
            for join_new_type in possible_new_join_types:
                join_new_type_str = join_new_type[0] or join_new_type[1]
                if join_target_type_str == "CROSS":
                    # In case we replace a CROSS JOIN, we need to add conditions since other join types require them.
                    base_table = statement.args.get("from_")
                    join_table = join_target.this
                    if base_table and isinstance(base_table.this, exp.Table) and isinstance(join_table.this, exp.Identifier):
                        base_table_name = base_table.name.lower()
                        join_table_name = join_table.name.lower()
                        if base_table_name in self.schema and join_table_name in self.schema\
                            and self.schema[base_table_name] and self.schema[join_table_name]:
                            base_col = self.schema[base_table_name][0]
                            join_col = self.schema[join_table_name][0]
                            condition = f"{base_table_name}.{base_col} = {join_table_name}.{join_col}"
                            desc = f"[Statement {statement_index}] Mutate CROSS JOIN to {join_new_type_str} JOIN with condition {condition}."
                            mutations.append((lambda block, ji=join_idx, jnt=join_new_type, cond=condition:
                                              self.mutate_join_clause(join_target=block.expressions[statement_index].args["joins"][ji],
                                                                      join_new_kind=jnt[0],
                                                                      join_new_side=jnt[1],
                                                                      sql_condition=cond), desc))
                        else:
                            logger.warning(f"Query {self.query_id} has a CROSS JOIN, but we cannot mutate it")
                else:
                    desc = f"[Statement {statement_index}] Mutate {join_target_type_str} JOIN to {join_new_type_str} JOIN."
                    mutations.append((lambda block, ji=join_idx, jnt=join_new_type:
                                      self.mutate_join_clause(join_target=block.expressions[statement_index].args["joins"][ji],
                                                              join_new_kind=jnt[0],
                                                              join_new_side=jnt[1],
                                                              sql_condition=None), desc))
        return mutations

    def mutate_join_clause(self, join_target: exp.Join, join_new_kind: str, join_new_side: str, sql_condition: str | None):
        join_target.set("kind", join_new_kind)
        join_target.set("side", join_new_side)
        if join_new_kind == "CROSS":
            join_target.set("on", None)
            join_target.set("using", None)
        if sql_condition is not None:
            join_target.set("on", exp.condition(sql_condition))
            join_target.set("using", None)
    
    def collect_mutations_subquery_predicate(self, statement: exp.Select, statement_index: int):
        targets = list(statement.find_all(exp.In, exp.Exists, exp.Any, exp.All))
        mutations = []
        for target_idx, target in enumerate(targets):
            def get_expression_copy(block, si=statement_index, ti=target_idx):
                return list(block.expressions[si].find_all(exp.In, exp.Exists, exp.Any, exp.All))[ti]
            if isinstance(target, exp.Any):
                mutations.append((lambda block, f=get_expression_copy: self.mutate_any_all(f(block), exp.All),
                                  f"[Statement {statement_index}] Replace ANY with ALL."))
            elif isinstance(target, exp.All):
                mutations.append((lambda block, f=get_expression_copy: self.mutate_any_all(f(block), exp.Any),
                                  f"[Statement {statement_index}] Replace ALL with ANY."))
            elif isinstance(target, exp.Exists):
                mutations.append((lambda block, f=get_expression_copy: self.mutate_exists_toggle(f(block)),
                                  f"[Statement {statement_index}] Toggle NOT on EXISTS."))
            elif isinstance(target, exp.In):
                # We can either toggle NOT on IN, or convert it to an EXISTS subquery (if it has a subquery).
                mutations.append((lambda block, f=get_expression_copy: self.mutate_in_toggle(f(block)),
                                  f"[Statement {statement_index}] Toggle NOT on IN."))
                if target.args.get("query") is not None:
                    mutations.append((lambda block, f=get_expression_copy: self.mutate_in_to_exists(f(block), is_not=False),
                                      f"[Statement {statement_index}] Replace IN with EXISTS."))
                    mutations.append((lambda block, f=get_expression_copy: self.mutate_in_to_exists(f(block), is_not=True),
                                      f"[Statement {statement_index}] Replace IN with NOT EXISTS."))
        return mutations

    def mutate_any_all(self, target: exp.Expr, new_class):
        target.replace(new_class(**target.args))

    def mutate_exists_toggle(self, target: exp.Exists):
        if isinstance(target.parent, exp.Not):
            target.parent.replace(target.copy())
        else:
            target.replace(exp.Not(this=target.copy()))

    def mutate_in_toggle(self, target: exp.In):
        if isinstance(target.parent, exp.Not):
            target.parent.replace(target.copy())
        else:
            target.replace(exp.Not(this=target.copy()))

    def mutate_in_to_exists(self, target: exp.In, is_not: bool):
        q = target.args.get("query")
        assert q is not None
        new_exists = exp.Exists(this=q.unnest().copy())
        replacement = exp.Not(this=new_exists) if is_not else new_exists
        if isinstance(target.parent, exp.Not):
            target.parent.replace(replacement)
        else:
            target.replace(replacement)
    
    def collect_mutations_group_by_clause(self, statement: exp.Select, statement_index: int):
        group = statement.args.get("group")
        if group is None:
            return []
        mutations = []
        for expr_idx in range(len(group.expressions)):
            desc = f"[Statement {statement_index}] Remove GROUP BY expression at index {expr_idx}."
            mutations.append((
                lambda block, si=statement_index, ei=expr_idx:
                    self.mutate_group_by_clause(block.expressions[si], block.expressions[si].args.get("group"), ei), desc))
        return mutations

    def mutate_group_by_clause(self, statement: exp.Select, group_target: exp.Group, expr_idx: int):
        group_expressions = group_target.expressions
        if len(group_expressions) == 1:
            statement.set("group", None)
            statement.set("having", None)
        else:
            expression_to_remove = group_expressions[expr_idx]
            identifier = expression_to_remove.this
            if isinstance(identifier, exp.Identifier):
                identifier_name = identifier.name.lower()
                # If the removed expression appears in SELECT or ORDER BY, we wrap it in an aggregate to keep the query valid.
                order_by = statement.args.get("order")
                if order_by is not None:
                    for order_expression in order_by.expressions:
                        column = order_expression.this
                        if isinstance(column.this, exp.Identifier) and column.this.name.lower() == identifier_name:
                            aggregate = random.choice([exp.Max, exp.Min])
                            order_expression.set("this", aggregate(this=expression_to_remove.copy()))
                for select_expression in statement.expressions:
                    if isinstance(select_expression.this, exp.Identifier) and select_expression.this.name.lower() == identifier_name:
                        aggregate = random.choice([exp.Max, exp.Min])
                        select_expression.set("this", aggregate(this=expression_to_remove.copy()))
            group_expressions.remove(expression_to_remove)        

    def get_agg_valid_targets(self, statement: exp.Select) -> List[Tuple[exp.AggFunc, str]]:
        targets = [(agg, "SELECT") for expr in statement.args.get("expressions", []) for agg in expr.find_all(exp.AggFunc)]
        if statement.args.get("having"):
            targets.extend([(agg, "HAVING") for agg in statement.args["having"].find_all(exp.AggFunc)])
        return [(agg, loc) for agg, loc in targets if agg.this is not None and not isinstance(agg.this, exp.Star)]
    
    def collect_mutations_aggregate_function(self, statement: exp.Select, statement_index: int):
        # We first collect all valid aggregate function targets in the SELECT and HAVING clauses.
        # For example, COUNT(*) cannot be mutated since SUM(*) and AVG(*) are not valid.
        targets = self.get_agg_valid_targets(statement)
        if not targets:
            return []
        
        mutations = []
        for target_idx, (agg, location) in enumerate(targets):
            arg = agg.this
            # Knowing the type of the argument can help us do more mutations.
            # TODO: We can potentially infer more types based on the schema.
            is_char = isinstance(arg, exp.Literal) and arg.is_string
            # COUNT(string) in HAVING compared to a number must stay as COUNT to remain valid.
            if location == "HAVING" and is_char and isinstance(agg, exp.Count):
                parent = agg.parent
                if isinstance(parent, (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.EQ, exp.NEQ)):
                    other = parent.right if parent.left is agg else parent.left
                    if isinstance(other, exp.Literal) and other.is_number:
                        continue
            agg_types = [exp.Max, exp.Min, exp.Count] if is_char else [exp.Max, exp.Min, exp.Avg, exp.Sum, exp.Count]
            current_type = type(agg)
            current_distinct = bool(agg.args.get("distinct"))
            for agg_type in agg_types:
                for distinct in [True, False]:
                    if agg_type == current_type and distinct == current_distinct:
                        continue
                    desc = (f"[Statement {statement_index}] Replace {current_type}{'(DISTINCT)' if current_distinct else ''} "
                            f"with {agg_type}{'(DISTINCT)' if distinct else ''} in {location}.")
                    mutations.append((
                        lambda block, si=statement_index, ti=target_idx, c=agg_type, d=distinct:
                            self.mutate_aggregate_function(self.get_agg_valid_targets(block.expressions[si])[ti][0], c, d), desc))
        return mutations

    def mutate_aggregate_function(self, aggregate_target: exp.AggFunc, new_type: type, new_distinct: bool):
        new_agg = new_type(this=aggregate_target.this.copy())
        if new_distinct:
            new_agg.set("distinct", exp.Distinct())
        aggregate_target.replace(new_agg)
    
    ############################### Operator Replacement Mutations ###############################
    def collect_mutations_relational_operator(self, statement: exp.Select, statement_index: int):
        targets = []
        for clause in [statement.args.get("where"), statement.args.get("having")]:
            if clause:
                targets.extend(clause.find_all(exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE))
        if not targets:
            return []
        relational_operators = [exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE]
        mutations = []
        for target_idx, target in enumerate(targets):
            options = [op for op in relational_operators if not isinstance(target, op)]
            options.extend(["falseop", "trueop"])
            for choice in options:
                choice_name = choice if isinstance(choice, str) else choice.__name__
                desc = f"[Statement {statement_index}] Replace relational operator at index {target_idx} with {choice_name}."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    stmt = block.expressions[si]
                    targets_copy = []
                    for clause in [stmt.args.get("where"), stmt.args.get("having")]:
                        if clause:
                            targets_copy.extend(clause.find_all(exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE))
                    self.mutate_relational_operator(targets_copy[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_relational_operator(self, target: exp.EQ | exp.NEQ | exp.LT | exp.LTE | exp.GT | exp.GTE, choice):
        if choice == "falseop":
            target.replace(exp.false())
        elif choice == "trueop":
            target.replace(exp.true())
        else:
            target.replace(choice(this=target.left.copy(), expression=target.right.copy()))

    def collect_mutations_logical_operator(self, statement: exp.Select, statement_index: int):
        targets = []
        for clause in [statement.args.get("where"), statement.args.get("having")]:
            if clause:
                targets.extend(clause.find_all(exp.And, exp.Or))
        if not targets:
            return []
        mutations = []
        for target_idx, target in enumerate(targets):
            options = [exp.Or if isinstance(target, exp.And) else exp.And, "falseop", "trueop", "leftop", "rightop"]
            for choice in options:
                choice_name = choice if isinstance(choice, str) else choice.__name__
                desc = f"[Statement {statement_index}] Replace logical operator at index {target_idx} with {choice_name}."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    stmt = block.expressions[si]
                    fresh_targets = []
                    for clause in [stmt.args.get("where"), stmt.args.get("having")]:
                        if clause:
                            fresh_targets.extend(clause.find_all(exp.And, exp.Or))
                    self.mutate_logical_operator(fresh_targets[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_logical_operator(self, target: exp.And | exp.Or, choice):
        if choice == "falseop":
            target.replace(exp.false())
        elif choice == "trueop":
            target.replace(exp.true())
        elif choice == "leftop":
            target.replace(target.left.copy())
        elif choice == "rightop":
            target.replace(target.right.copy())
        else:
            target.replace(choice(this=target.left.copy(), expression=target.right.copy()))

    def get_valid_arithmetic_targets(self, statement: exp.Select) -> List[exp.Expr]:
        targets = []
        for node in statement.find_all(exp.Literal, exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod):
            if isinstance(node, exp.Literal) and not node.is_number:
                continue
            is_excluded = False
            current = node
            while current:
                if isinstance(current, (exp.Group, exp.Order)):
                    is_excluded = True
                    break
                if isinstance(current, exp.Exists):
                    if current.this and current.this.args.get("expressions"):
                        for expr in current.this.args.get("expressions"):
                            if expr == node or node in list(expr.find_all(type(node))):
                                is_excluded = True
                                break
                    break
                current = current.parent
            if not is_excluded:
                targets.append(node)
        return targets

    def collect_mutations_unary_operator(self, statement: exp.Select, statement_index: int):
        targets = self.get_valid_arithmetic_targets(statement)
        if not targets:
            return []
        mutations = []
        for target_idx in range(len(targets)):
            for choice in ["negate", "add1", "sub1"]:
                desc = f"[Statement {statement_index}] Apply {choice} to arithmetic expression at index {target_idx}."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    self.mutate_unary_operator(self.get_valid_arithmetic_targets(block.expressions[si])[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_unary_operator(self, target: exp.Expr, choice: str):
        if choice == "negate":
            target.replace(exp.Neg(this=target.copy()))
        elif choice == "add1":
            target.replace(exp.Add(this=target.copy(), expression=exp.Literal.number(1)))
        elif choice == "sub1":
            target.replace(exp.Sub(this=target.copy(), expression=exp.Literal.number(1)))

    def collect_mutations_absolute_value(self, statement: exp.Select, statement_index: int):
        targets = self.get_valid_arithmetic_targets(statement)
        if not targets:
            return []
        mutations = []
        for target_idx in range(len(targets)):
            for choice in ["abs", "neg_abs"]:
                desc = f"[Statement {statement_index}] Apply {choice} to arithmetic expression at index {target_idx}."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    self.mutate_absolute_value(self.get_valid_arithmetic_targets(block.expressions[si])[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_absolute_value(self, target: exp.Expr, choice: str):
        abs_func = exp.func("ABS", target.copy())
        if choice == "abs":
            target.replace(abs_func)
        elif choice == "neg_abs":
            target.replace(exp.Neg(this=abs_func))

    def collect_mutations_arithmetic_operator(self, statement: exp.Select, statement_index: int):
        targets = list(statement.find_all(exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod))
        if not targets:
            return []
        arithmetic_classes = [exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod]
        mutations = []
        for target_idx, target in enumerate(targets):
            options = [cls for cls in arithmetic_classes if not isinstance(target, cls)]
            options.extend(["leftop", "rightop"])
            for choice in options:
                choice_name = choice if isinstance(choice, str) else choice.__name__
                desc = f"[Statement {statement_index}] Replace arithmetic operator at index {target_idx} with {choice_name}."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    fresh_targets = list(block.expressions[si].find_all(exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod))
                    self.mutate_arithmetic_operator(fresh_targets[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_arithmetic_operator(self, target: exp.Add | exp.Sub | exp.Mul | exp.Div | exp.Mod, choice):
        if choice == "leftop":
            target.replace(target.left.copy())
        elif choice == "rightop":
            target.replace(target.right.copy())
        else:
            target.replace(choice(this=target.left.copy(), expression=target.right.copy()))

    def collect_mutations_between(self, statement: exp.Select, statement_index: int):
        targets = list(statement.find_all(exp.Between))
        if not targets:
            return []
        mutations = []
        for target_idx in range(len(targets)):
            for choice in [1, 2]:
                desc = f"[Statement {statement_index}] Replace BETWEEN at index {target_idx} with explicit inequalities (Option {choice})."
                def apply(block, si=statement_index, ti=target_idx, c=choice):
                    fresh_targets = list(block.expressions[si].find_all(exp.Between))
                    self.mutate_between(fresh_targets[ti], c)
                mutations.append((apply, desc))
        return mutations

    def mutate_between(self, target: exp.Between, choice: int):
        a, x, y = target.this.copy(), target.args["low"].copy(), target.args["high"].copy()
        if choice == 1:
            cond = exp.And(this=exp.GT(this=a.copy(), expression=x), expression=exp.LTE(this=a.copy(), expression=y))
        else:
            cond = exp.And(this=exp.GTE(this=a.copy(), expression=x), expression=exp.LT(this=a.copy(), expression=y))
        if isinstance(target.parent, exp.Not):
            target.parent.replace(exp.Not(this=cond))
        else:
            target.replace(cond)

    def collect_mutations_like_patterns(self, statement: exp.Select, statement_index: int):
        all_targets = list(statement.find_all(exp.Like, exp.ILike))
        valid_targets = [t for t in all_targets if isinstance(t.expression, exp.Literal) and t.expression.is_string]
        if not valid_targets:
            return []
        mutations = []
        for target_idx, target in enumerate(valid_targets):
            pattern = target.expression.name
            if not pattern:
                continue
            new_patterns: set[str] = set()
            wildcards = [(i, ch) for i, ch in enumerate(pattern) if ch in ('%', '_')]
            for idx, char in wildcards:
                other = '_' if char == '%' else '%'
                new_patterns.add(pattern[:idx] + pattern[idx+1:])
                new_patterns.add(pattern[:idx] + other + pattern[idx+1:])
                if idx > 0 and pattern[idx-1] not in ('%', '_'):
                    new_patterns.add(pattern[:idx-1] + pattern[idx:])
                if idx < len(pattern) - 1 and pattern[idx+1] not in ('%', '_'):
                    new_patterns.add(pattern[:idx+1] + pattern[idx+2:])
            if not pattern.startswith(('%', '_')):
                new_patterns.update(['%' + pattern, '_' + pattern])
            if not pattern.endswith(('%', '_')):
                new_patterns.update([pattern + '%', pattern + '_'])
            for new_pattern in new_patterns:
                desc = f"[Statement {statement_index}] Mutate LIKE pattern at index {target_idx} from '{pattern}' to '{new_pattern}'."
                def apply(block, si=statement_index, ti=target_idx, np=new_pattern):
                    stmt = block.expressions[si]
                    fresh_all = list(stmt.find_all(exp.Like, exp.ILike))
                    fresh_valid = [t for t in fresh_all if isinstance(t.expression, exp.Literal) and t.expression.is_string]
                    self.mutate_like_pattern(fresh_valid[ti], np)
                mutations.append((apply, desc))
        return mutations

    def mutate_like_pattern(self, target: exp.Expr, new_pattern: str):
        target.expression.set("this", new_pattern)