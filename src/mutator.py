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
        self.query_id = None

    @timed("mutation")
    def mutate(self, query: str, query_id: str, num_mutations: int = 1) -> List[str]:
        """Main entrypoint for mutating a query. We are given the base query in the string format.
        We will parse it into an AST, and return up to `num_mutations` mutated versions of the query as strings."""
        query_parsed: exp.Expr = sqlglot.parse_one(query, read=self.dialect)
        if not isinstance(query_parsed, exp.Block):
            logger.warning(f"Expected a block of statements at the top level for query {query_id}")
            return []
        
        # We want to start by collecting all available mutations.
        self.schema = {}
        self.query_id = query_id
        available_mutations: List[Tuple[Callable[[None], None], str]] = []
        block: exp.Block = query_parsed
        for i, statement in enumerate(block.expressions):
            self.update_schema(statement, query_id)
            if isinstance(statement, exp.Select):
                # Mutation 1: Toggle DISTINCT in the SELECT clause.
                available_mutations.extend(self.collect_mutations_select_clause(statement, i))

                # Mutation 2: Mutate the JOIN clause (change type, add/remove conditions).
                # The join types are: INNER, LEFT, RIGHT, FULL, CROSS.
                # They are characterized by the pair (kind, side).
                available_mutations.extend(self.collect_mutations_join_clause(statement, i))

                # Mutation 3: Mutate subquery predicates (EXISTS, IN, ANY, ALL).
                # The predicate can be of the following types:
                # - Type I: All, Any;
                # - Type II: In, Not In;
                # - Type III: Exists, Not Exists.
                available_mutations.extend(self.collect_mutations_subquery_predicate(statement, i))

                # Mutation 4: Remove expressions from the GROUP BY clause.
                available_mutations.extend(self.collect_mutations_group_by_clause(statement, i))

                # Mutation 5: Mutate aggregate functions (change function, add/remove DISTINCT).
                available_mutations.extend(self.collect_mutations_aggregate_function(statement, i))
        # print(available_mutations)                
        mutations_to_apply = random.sample(available_mutations, min(num_mutations, len(available_mutations)))
        for mutation_func, _ in mutations_to_apply:
            mutation_func(None)
        return [query_parsed.sql(dialect=self.dialect)]

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
    def collect_mutations_select_clause(self, statement: exp.Select, statement_index: int):
        desc = f"[Statement {statement_index}] Toggle DISTINCT in SELECT clause."
        return [(lambda _: self.mutate_select_clause(statement), desc)]

    def mutate_select_clause(self, statement: exp.Select):
        is_distinct = statement.args.get("distinct")
        statement.set("distinct", exp.Distinct() if not is_distinct else None)
    
    def collect_mutations_join_clause(self, statement: exp.Select, statement_index: int):
        join_types = [("CROSS", None), ("INNER", None), (None, "LEFT"), (None, "RIGHT"), (None, "FULL")]
        joins = statement.args.get("joins")
        if joins is None:
            return []
        join_target: exp.Join = random.choice(joins)
        join_target_type = (join_target.args.get("kind"), join_target.args.get("side"))
        join_target_type_str = join_target.args.get("kind") or join_target.args.get("side")
        join_new_type = random.choice([jt for jt in join_types if jt != join_target_type])
        join_new_type_str = join_new_type[0] or join_new_type[1]
        if join_target.args.get("kind") == "CROSS":
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
                    return [(lambda _: self.mutate_join_clause(join_target, join_new_type[0], join_new_type[1], condition), desc)]
                else:
                    logger.warning(f"Query {self.query_id} has a CROSS JOIN, but we cannot mutate it")
                    return []
            else:
                # In case of join of subqueries we don't have schema information.
                return []
        else:
            desc = f"[Statement {statement_index}] Mutate {join_target_type_str} JOIN to {join_new_type_str} JOIN."
            return [(lambda _: self.mutate_join_clause(join_target, join_new_type[0], join_new_type[1], None), desc)]

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
        if not targets:
            return []
        subqeury_predicate_target = random.choice(targets)
        desc = f"[Statement {statement_index}] Mutate a subquery predicate of type {type(subqeury_predicate_target).__name__}."
        return [(lambda _: self.mutate_subquery_predicate(subqeury_predicate_target), desc)]

    def mutate_subquery_predicate(self, predicate_target: exp.Expr):
        if isinstance(predicate_target, (exp.All, exp.Any)):
            new_class = exp.All if isinstance(predicate_target, exp.Any) else exp.Any
            predicate_target.replace(new_class(**predicate_target.args))
        elif isinstance(predicate_target, exp.Exists):
            if isinstance(predicate_target.parent, exp.Not):
                predicate_target.parent.replace(predicate_target.copy())
            else:
                predicate_target.replace(exp.Not(this=predicate_target.copy()))
        elif isinstance(predicate_target, exp.In):
            q = predicate_target.args.get("query")
            new_type = random.choice(["typeII", "typeIII"])
            if q is None:
                new_type = "typeII"
            if new_type == "typeII":
                if isinstance(predicate_target.parent, exp.Not):
                    predicate_target.parent.replace(predicate_target.copy())
                else:
                    predicate_target.replace(exp.Not(this=predicate_target.copy()))
            elif new_type == "typeIII":
                assert q is not None, "Expected to have a subquery for type III mutation."
                is_not_exists = random.choice([True, False])
                clean_q = q.unnest().copy()
                new_exists = exp.Exists(this=clean_q)
                if isinstance(predicate_target.parent, exp.Not):
                    predicate_target.parent.replace(exp.Not(this=new_exists) if is_not_exists else new_exists)
                else:
                    predicate_target.replace(exp.Not(this=new_exists) if is_not_exists else new_exists)
    
    def collect_mutations_group_by_clause(self, statement: exp.Select, statement_index: int):
        group = statement.args.get("group")
        if group is None:
            return []
        desc = f"[Statement {statement_index}] Remove expression from the GROUP BY clause."
        return [(lambda _: self.mutate_group_by_clause(statement, group), desc)]

    def mutate_group_by_clause(self, statement: exp.Select, group_target: exp.Group):
        group_expressions = group_target.expressions
        if len(group_expressions) == 1:
            statement.set("group", None)
            statement.set("having", None)
        else:
            expression_to_remove = random.choice(group_expressions)
            identifier = expression_to_remove.this
            if isinstance(identifier, exp.Identifier):
                identifier_name = identifier.name.lower()
                # In order to remove an expression from the GROUP BY clause
                # and keep the query valid, we also need to check if it is ia present in
                # the SELECT clause and the ORDER BY clause. If it's there, we will
                # wrap it in an aggregate function instead of removing it.
                order_by = statement.args.get("order")
                if order_by is not None:
                    for order_expression in order_by.expressions:
                        column = order_expression.this
                        if isinstance(column.this, exp.Identifier) and column.this.name.lower() == identifier_name:
                            aggregate = random.choice([exp.Max, exp.Min])
                            order_expression.set("this", aggregate(this=expression_to_remove.copy()))
                select_expressions = statement.expressions
                if select_expressions is not None:
                    for select_expression in select_expressions:
                        if isinstance(select_expression.this, exp.Identifier) and select_expression.this.name.lower() == identifier_name:
                            aggregate = random.choice([exp.Max, exp.Min])
                            select_expression.set("this", aggregate(this=expression_to_remove.copy()))
                group_expressions.remove(expression_to_remove)

    def collect_mutations_aggregate_function(self, statement: exp.Select, statement_index: int):
        targets = []
        for expr in statement.args.get("expressions", []):
            targets.extend([(agg, "SELECT") for agg in expr.find_all(exp.AggFunc)])
        having_clause = statement.args.get("having")
        if having_clause:
            targets.extend([(agg, "HAVING") for agg in having_clause.find_all(exp.AggFunc)])
        # We cannot mutate COUNT(*) since SUM(*) and AVG(*) are not valid, so we filter out those cases.
        valid_targets = [t for t in targets if t[0].this is not None and not isinstance(t[0].this, exp.Star)]
        if not valid_targets:
            return []
        
        aggregation_target, location = random.choice(valid_targets)
        desc = f"[Statement {statement_index}] Mutate the aggregate function {aggregation_target} in the {location} clause."
        return [(lambda _: self.mutate_aggregate_function(aggregation_target, location), desc)]

    def mutate_aggregate_function(self, aggregate_target: exp.AggFunc, location: str):
        # We identify the data type of the argument to the aggregate function.
        # This allows us to make sure that the query is valid.
        arg = aggregate_target.this 
        is_char = False
        if isinstance(arg, exp.Literal) and arg.is_string:
            is_char = True
        
        if location == "HAVING" and is_char and isinstance(aggregate_target, exp.Count):
            parent = aggregate_target.parent
            if isinstance(parent, (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.EQ, exp.NEQ)):
                other_operand = parent.right if parent.left is aggregate_target else parent.left
                if isinstance(other_operand, exp.Literal) and other_operand.is_number:
                    return
                    
        agg_classes = [exp.Max, exp.Min, exp.Avg, exp.Sum, exp.Count]
        if is_char:
            agg_classes = [exp.Max, exp.Min, exp.Count]  
        current_cls = type(aggregate_target)
        current_distinct = bool(aggregate_target.args.get("distinct"))
        
        options = []
        for cls in agg_classes:
            for distinct in [True, False]:
                if cls == current_cls and distinct == current_distinct:
                    continue
                options.append((cls, distinct))        
        if not options:
            return
            
        new_cls, new_distinct = random.choice(options)
        new_agg = new_cls(this=arg.copy())
        if new_distinct:
            new_agg.set("distinct", exp.Distinct())
        aggregate_target.replace(new_agg)
    
    ############################### OR: Operator Replacement Mutations ###############################

    def _mutate_ror(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """ROR - Relational operator replacement"""
        # Targeting WHERE and HAVING clauses
        targets = []
        for clause in [statement.args.get("where"), statement.args.get("having")]:
            if clause:
                targets.extend(list(clause.find_all(
                    exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE
                )))
        
        if not targets:
            return "None"
            
        target = random.choice(targets)
        relational_classes = [exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE]
        
        # Options: (1) Other operators, (2) falseop, (3) trueop
        options = [cls for cls in relational_classes if not isinstance(target, cls)]
        options.extend(["falseop", "trueop"])
        
        choice = random.choice(options)
        
        if choice == "falseop":
            target.replace(exp.false())
            return "ROR: Replaced relational operator with FALSE."
        elif choice == "trueop":
            target.replace(exp.true())
            return "ROR: Replaced relational operator with TRUE."
        else:
            new_node = choice(this=target.left.copy(), expression=target.right.copy())
            target.replace(new_node)
            return f"ROR: Replaced relational operator with {choice.__name__}."

    def _mutate_lcr(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """LCR - Logical connector operator"""
        targets = []
        for clause in [statement.args.get("where"), statement.args.get("having")]:
            if clause:
                targets.extend(list(clause.find_all(exp.And, exp.Or)))
                
        if not targets:
            return "None"
            
        target = random.choice(targets)
        
        # Options: (1) Other operator, (2) falseop, (3) trueop, (4) leftop, (5) rightop
        options = [
            exp.Or if isinstance(target, exp.And) else exp.And,
            "falseop", "trueop", "leftop", "rightop"
        ]
        
        choice = random.choice(options)
        
        if choice == "falseop":
            target.replace(exp.false())
        elif choice == "trueop":
            target.replace(exp.true())
        elif choice == "leftop":
            target.replace(target.left.copy())
        elif choice == "rightop":
            target.replace(target.right.copy())
        else:
            new_node = choice(this=target.left.copy(), expression=target.right.copy())
            target.replace(new_node)
            
        return f"LCR: Mutated logical connector ({choice if isinstance(choice, str) else choice.__name__})."

    def _get_valid_arithmetic_targets(self, statement: exp.Select) -> List[exp.Expr]:
        """Helper to find valid targets for UOI and ABS."""
        targets = []
        for node in statement.find_all(exp.Literal, exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod):
            # Only consider numeric literals or arithmetic expressions
            if isinstance(node, exp.Literal) and not node.is_number:
                continue
                
            # Exclude GROUP BY, ORDER BY, and SELECT lists of EXISTS
            is_excluded = False
            current = node
            while current:
                if isinstance(current, (exp.Group, exp.Order)):
                    is_excluded = True
                    break
                if isinstance(current, exp.Exists):
                    # Check if it's inside the select list of the EXISTS subquery
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

    def _mutate_uoi(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """UOI - Unary Operator Insertion"""
        targets = self._get_valid_arithmetic_targets(statement)
        if not targets:
            return "None"
            
        target = random.choice(targets)
        
        # Options: -e, e+1, e-1
        options = ["negate", "add1", "sub1"]
        choice = random.choice(options)
        
        if choice == "negate":
            target.replace(exp.Neg(this=target.copy()))
        elif choice == "add1":
            target.replace(exp.Add(this=target.copy(), expression=exp.Literal.number(1)))
        elif choice == "sub1":
            target.replace(exp.Sub(this=target.copy(), expression=exp.Literal.number(1)))
            
        return f"UOI: Applied {choice} to arithmetic expression."

    def _mutate_abs(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """ABS - Absolute Value Insertion"""
        targets = self._get_valid_arithmetic_targets(statement)
        if not targets:
            return "None"
            
        target = random.choice(targets)
        choice = random.choice(["abs", "neg_abs"])
        
        abs_func = exp.func("ABS", target.copy())
        
        if choice == "abs":
            target.replace(abs_func)
        elif choice == "neg_abs":
            target.replace(exp.Neg(this=abs_func))
            
        return f"ABS: Applied {choice} to arithmetic expression."

    def _mutate_aor(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """AOR - Arithmetic operator replacement"""
        targets = list(statement.find_all(exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod))
        if not targets:
            return "None"
            
        target = random.choice(targets)
        arithmetic_classes = [exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod]
        
        options = [cls for cls in arithmetic_classes if not isinstance(target, cls)]
        options.extend(["leftop", "rightop"])
        
        choice = random.choice(options)
        
        if choice == "leftop":
            target.replace(target.left.copy())
        elif choice == "rightop":
            target.replace(target.right.copy())
        else:
            new_node = choice(this=target.left.copy(), expression=target.right.copy())
            target.replace(new_node)
            
        return "AOR: Mutated arithmetic operator."

    def _mutate_btw(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """BTW - Between predicate"""
        targets = list(statement.find_all(exp.Between))
        if not targets:
            return "None"
            
        target = random.choice(targets)
        a = target.this.copy()
        x = target.args.get("low").copy()
        y = target.args.get("high").copy()
        is_not = isinstance(target.parent, exp.Not)
        
        # Options: 
        # (1) a > x AND a <= y
        # (2) a >= x AND a < y
        choice = random.choice([1, 2])
        
        if choice == 1:
            cond = exp.And(this=exp.GT(this=a.copy(), expression=x), 
                           expression=exp.LTE(this=a.copy(), expression=y))
        else:
            cond = exp.And(this=exp.GTE(this=a.copy(), expression=x), 
                           expression=exp.LT(this=a.copy(), expression=y))
                           
        if is_not:
            cond = exp.Not(this=cond)
            target.parent.replace(cond)
        else:
            target.replace(cond)
            
        return f"BTW: Replaced BETWEEN with explicit inequalities (Option {choice})."

    def _mutate_lke(self, statement: exp.Select, context: List[exp.Expr]) -> str:
        """LKE - Like predicate"""
        targets = list(statement.find_all(exp.Like, exp.ILike))
        # Filter for targets where the right side is a static string literal
        valid_targets = [t for t in targets if isinstance(t.expression, exp.Literal) and t.expression.is_string]
        
        if not valid_targets:
            return "None"
            
        target = random.choice(valid_targets)
        pattern = target.expression.name
        
        if not pattern:
            return "None"
            
        wildcards = [(i, char) for i, char in enumerate(pattern) if char in ('%', '_')]
        mutations = []
        
        # Build possible string mutations based on wildcard presence
        if wildcards:
            idx, char = random.choice(wildcards)
            other_char = '_' if char == '%' else '%'
            
            # (1) Remove wildcard
            mutations.append(pattern[:idx] + pattern[idx+1:])
            # (2) Swap wildcard
            mutations.append(pattern[:idx] + other_char + pattern[idx+1:])
            # (3) Remove char before
            if idx > 0 and pattern[idx-1] not in ('%', '_'):
                mutations.append(pattern[:idx-1] + pattern[idx:])
            # (4) Remove char after
            if idx < len(pattern) - 1 and pattern[idx+1] not in ('%', '_'):
                mutations.append(pattern[:idx+1] + pattern[idx+2:])
        
        # (5) Add wildcard at beginning if not present
        if not pattern.startswith(('%', '_')):
            mutations.append('%' + pattern)
            mutations.append('_' + pattern)
            
        # (6) Add wildcard at end if not present
        if not pattern.endswith(('%', '_')):
            mutations.append(pattern + '%')
            mutations.append(pattern + '_')
            
        if not mutations:
            return "None"
            
        new_pattern = random.choice(mutations)
        target.expression.set("this", new_pattern)
        
        return f"LKE: Mutated LIKE wildcard pattern."