import random
from sqlglot import exp
from typing import List, Tuple, Callable, Dict
from loguru import logger
from .common import collect_mutations_extreme_values, collect_mutations_relational_operators, collect_mutations_logical_operators, \
    collect_mutations_insert_unary_operator, collect_mutations_arithmetic_binary_operators, collect_mutations_between, \
    collect_mutations_like_patterns, collect_mutations_null_check

SelectMutation = Tuple[Callable[[exp.Select], None], str]

################################### Mutations for SELECT statements ###################################
def collect(statement: exp.Select, schema: Dict[str, List[str]]) -> List[SelectMutation]:
    mutations: List[SelectMutation] = []
    # Here are mutations specific to the SELECT statement.
    mutations.extend(collect_mutations_select_clause(statement))
    mutations.extend(collect_mutations_where_clause(statement))
    mutations.extend(collect_mutations_join_clause(statement, schema))
    mutations.extend(collect_mutations_subquery_predicate(statement))
    mutations.extend(collect_mutations_group_by_clause(statement))
    mutations.extend(collect_mutations_aggregate_function(statement))
    mutations.extend(collect_mutations_having_clause(statement))
    mutations.extend(collect_mutations_order_by(statement))
    mutations.extend(collect_mutations_case_when(statement))
    # Here are mutations that can apply to any statement type.
    mutations.extend(collect_mutations_extreme_values(statement))
    mutations.extend(collect_mutations_relational_operators(statement))
    mutations.extend(collect_mutations_logical_operators(statement))
    mutations.extend(collect_mutations_insert_unary_operator(statement))
    mutations.extend(collect_mutations_arithmetic_binary_operators(statement))
    mutations.extend(collect_mutations_between(statement))
    mutations.extend(collect_mutations_like_patterns(statement))
    mutations.extend(collect_mutations_null_check(statement))
    return mutations

def collect_mutations_select_clause(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 1: Toggle DISTINCT in the SELECT clause and drop individual columns.
    mutations: List[SelectMutation] = []
    desc = f"Toggle DISTINCT in SELECT clause."
    mutations.append((lambda stmt: stmt.set("distinct", exp.Distinct() if not stmt.args.get("distinct") else None), desc))
    exprs = statement.args.get("expressions", [])
    is_star = len(exprs) == 1 and isinstance(exprs[0], exp.Star)
    if not is_star and len(exprs) > 1:
        for expr_idx in range(len(exprs)):
            desc = f"Drop SELECT expression at index {expr_idx}."
            def apply(stmt, ei=expr_idx):
                stmt.args["expressions"].pop(ei)
            mutations.append((apply, desc))
    return mutations

def collect_mutations_where_clause(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 2: Negate the WHERE clause condition, or drop it entirely.
    mutations: List[SelectMutation] = []
    where = statement.args.get("where")
    if not where:
        return mutations
    condition = where.this
    desc = f"Negate the WHERE clause condition."
    mutations.append((lambda stmt: stmt.set("where", exp.Where(this=exp.Not(this=stmt.args["where"].this.copy()))), desc))
    # If the condition is already a negation, we can also remove the NOT.
    if isinstance(condition, exp.Not):
        desc = f"Remove NOT from the WHERE clause condition."
        mutations.append((lambda stmt: stmt.set("where", exp.Where(this=stmt.args["where"].this.this.copy())), desc))
    desc = f"Drop the WHERE clause entirely."
    mutations.append((lambda stmt: stmt.set("where", None), desc))
    return mutations

def collect_mutations_join_clause(statement: exp.Select, schema: Dict[str, List[str]]) -> List[SelectMutation]:
    # Mutation 3: Mutate the JOIN clause (change type, add/remove conditions).
    # The join types are: INNER, LEFT, RIGHT, FULL, CROSS.
    # They are characterized by the pair (kind, side).
    mutations: List[SelectMutation] = []
    join_types = [("CROSS", None), ("INNER", None), (None, "LEFT"), (None, "RIGHT"), (None, "FULL")]
    joins = statement.args.get("joins", [])
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
                    if base_table_name in schema and join_table_name in schema\
                        and schema[base_table_name] and schema[join_table_name]:
                        base_col = schema[base_table_name][0]
                        join_col = schema[join_table_name][0]
                        condition = f"{base_table_name}.{base_col} = {join_table_name}.{join_col}"
                        desc = f"Mutate CROSS JOIN to {join_new_type_str} JOIN with condition {condition}."
                        mutations.append((lambda stmt, ji=join_idx, jnt=join_new_type, cond=condition:
                                          mutate_join_clause(join_target=stmt.args["joins"][ji],
                                                             join_new_kind=jnt[0],
                                                             join_new_side=jnt[1],
                                                             sql_condition=cond), desc))
                    else:
                        logger.warning(f"Query has a CROSS JOIN, but we cannot mutate it.")
            else:
                desc = f"Mutate {join_target_type_str} JOIN to {join_new_type_str} JOIN."
                mutations.append((lambda stmt, ji=join_idx, jnt=join_new_type:
                                  mutate_join_clause(join_target=stmt.args["joins"][ji],
                                                     join_new_kind=jnt[0],
                                                     join_new_side=jnt[1],
                                                     sql_condition=None), desc))
    return mutations

def mutate_join_clause(join_target: exp.Join, join_new_kind: str, join_new_side: str, sql_condition: str | None):
    join_target.set("kind", join_new_kind)
    join_target.set("side", join_new_side)
    if join_new_kind == "CROSS":
        join_target.set("on", None)
        join_target.set("using", None)
    if sql_condition is not None:
        join_target.set("on", exp.condition(sql_condition))
        join_target.set("using", None)

def collect_mutations_subquery_predicate(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 4: Mutate subquery predicates (EXISTS, IN, ANY, ALL).
    # There are several types of such predicates:
    # Type I: [ANY, ALL];
    # Type II: [IN, NOT IN];
    # Type III: [EXISTS, NOT EXISTS].
    mutations: List[SelectMutation] = []
    targets = list(statement.find_all(exp.In, exp.Exists, exp.Any, exp.All))
    for target_idx, target in enumerate(targets):
        get_copy_expr = lambda stmt, ti=target_idx: list(stmt.find_all(exp.In, exp.Exists, exp.Any, exp.All))[ti]
        if isinstance(target, exp.Any):
            mutations.append((lambda stmt, f=get_copy_expr: mutate_any_all(f(stmt), exp.All), f"Replace ANY with ALL."))
        elif isinstance(target, exp.All):
            mutations.append((lambda stmt, f=get_copy_expr: mutate_any_all(f(stmt), exp.Any), f"Replace ALL with ANY."))
        elif isinstance(target, exp.Exists):
            mutations.append((lambda stmt, f=get_copy_expr: mutate_exists_toggle_not(f(stmt)), f"Toggle NOT on EXISTS."))
        elif isinstance(target, exp.In):
            # We can either toggle NOT on IN, or convert it to an EXISTS subquery (if it has a subquery).
            mutations.append((lambda stmt, f=get_copy_expr: mutate_in_toggle_not(f(stmt)), f"Toggle NOT on IN."))
            if target.args.get("query") is not None:
                mutations.append((lambda stmt, f=get_copy_expr: mutate_in_to_exists(f(stmt), is_not=False), f"Replace IN with EXISTS."))
                mutations.append((lambda stmt, f=get_copy_expr: mutate_in_to_exists(f(stmt), is_not=True), f"Replace IN with NOT EXISTS."))
    return mutations

def mutate_any_all(target: exp.Expr, new_type: type[exp.Any] | type[exp.All]):
    target.replace(new_type(**target.args))

def mutate_exists_toggle_not(target: exp.Exists):
    if isinstance(target.parent, exp.Not):
        target.parent.replace(target.copy())
    else:
        target.replace(exp.Not(this=target.copy()))

def mutate_in_toggle_not(target: exp.In):
    if isinstance(target.parent, exp.Not):
        target.parent.replace(target.copy())
    else:
        target.replace(exp.Not(this=target.copy()))

def mutate_in_to_exists(target: exp.In, is_not: bool):
    q = target.args.get("query")
    assert q is not None, "Expected an IN predicate with a subquery for this mutation."
    new_exists = exp.Exists(this=q.unnest().copy())
    replacement = exp.Not(this=new_exists) if is_not else new_exists
    if isinstance(target.parent, exp.Not):
        target.parent.replace(replacement)
    else:
        target.replace(replacement)

def collect_mutations_group_by_clause(statement: exp.Select):
    # Mutation 5: Remove expressions from the GROUP BY clause.
    group = statement.args.get("group")
    if group is None:
        return []
    mutations: List[SelectMutation] = []
    for expr_idx in range(len(group.expressions)):
        desc = f"Remove GROUP BY expression at index {expr_idx}."
        def apply(stmt, ei=expr_idx):
            assert isinstance(stmt.args.get("group"), exp.Group), "Expected GROUP BY clause to be present for this mutation."
            mutate_group_by_clause(stmt, stmt.args.get("group"), ei)
        mutations.append((apply, desc))
    return mutations

def mutate_group_by_clause(statement: exp.Select, group_target: exp.Group, expr_idx: int):
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

def collect_mutations_aggregate_function(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 6: Mutate aggregate functions (change function, add/remove DISTINCT).
    targets = get_aggregate_valid_targets(statement)
    if not targets:
        return []
    mutations: List[SelectMutation] = []
    for target_idx, (agg, location) in enumerate(targets):
        arg = agg.this
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
                desc = (f"Replace {current_type.__name__}{'(DISTINCT)' if current_distinct else ''} "
                        f"with {agg_type.__name__}{'(DISTINCT)' if distinct else ''} in {location}.")
                mutations.append((
                    lambda stmt, ti=target_idx, c=agg_type, d=distinct:
                        mutate_aggregate_function(get_aggregate_valid_targets(stmt)[ti][0], c, d), desc))
    return mutations

def get_aggregate_valid_targets(statement: exp.Select) -> List[Tuple[exp.AggFunc, str]]:
    targets = [(agg, "SELECT") for expr in statement.args.get("expressions", []) for agg in expr.find_all(exp.AggFunc)]
    if statement.args.get("having"):
        targets.extend([(agg, "HAVING") for agg in statement.args["having"].find_all(exp.AggFunc)])
    return [(agg, loc) for agg, loc in targets if agg.this is not None and not isinstance(agg.this, exp.Star)]

def mutate_aggregate_function(target: exp.AggFunc, new_type: type, new_distinct: bool):
    new_agg = new_type(this=target.this.copy())
    if new_distinct:
        new_agg.set("distinct", exp.Distinct())
    target.replace(new_agg)

def collect_mutations_having_clause(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 7: Negate the HAVING clause condition, or drop it entirely.
    mutations: List[SelectMutation] = []
    having = statement.args.get("having")
    if not having:
        return mutations
    condition = having.this
    desc = f"Negate the HAVING clause condition."
    mutations.append((lambda stmt: stmt.set("having", exp.Having(this=exp.Not(this=stmt.args["having"].this.copy()))), desc))
    # If the condition is already a negation, we can also remove the NOT.
    if isinstance(condition, exp.Not):
        desc = f"Remove NOT from the HAVING clause condition."
        mutations.append((lambda stmt: stmt.set("having", exp.Having(this=stmt.args["having"].this.this.copy())), desc))
    desc = f"Drop the HAVING clause entirely."
    mutations.append((lambda stmt: stmt.set("having", None), desc))
    return mutations

def collect_mutations_order_by(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 8: Flip ORDER BY direction or remove ORDER BY expressions.
    order = statement.args.get("order")
    if order is None:
        return []
    mutations: List[SelectMutation] = []
    for expr_idx, ordered in enumerate(order.expressions):
        current_desc = bool(ordered.args.get("desc"))
        flip_str = "ASC" if current_desc else "DESC"
        def apply_flip(stmt, ei=expr_idx, d=not current_desc):
            stmt.args["order"].expressions[ei].set("desc", d)
        mutations.append((apply_flip, f"Flip ORDER BY expression at index {expr_idx} to {flip_str}."))
        def apply_remove(stmt, ei=expr_idx):
            order_exprs = stmt.args["order"].expressions
            if len(order_exprs) == 1:
                stmt.set("order", None)
            else:
                order_exprs.pop(ei)
        mutations.append((apply_remove, f"Remove ORDER BY expression at index {expr_idx}."))
    return mutations

def collect_mutations_case_when(statement: exp.Select) -> List[SelectMutation]:
    # Mutation 9: Mutate CASE WHEN expressions.
    cases = list(statement.find_all(exp.Case))
    if not cases:
        return []
    mutations: List[SelectMutation] = []
    for case_idx, case in enumerate(cases):
        ifs = case.args.get("ifs", [])
        default = case.args.get("default")
        if default is not None:
            for branch_idx in range(len(ifs)):
                desc = f"Swap THEN at branch {branch_idx} with ELSE in CASE at index {case_idx}."
                def apply_swap_else(stmt, ci=case_idx, bi=branch_idx):
                    c = list(stmt.find_all(exp.Case))[ci]
                    old_then = c.args["ifs"][bi].args["true"].copy()
                    c.args["ifs"][bi].set("true", c.args["default"].copy())
                    c.set("default", old_then)
                mutations.append((apply_swap_else, desc))
        for i in range(len(ifs)):
            for j in range(i + 1, len(ifs)):
                desc = f"Swap THEN at branches {i} and {j} in CASE at index {case_idx}."
                def apply_swap_branches(stmt, ci=case_idx, bi=i, bj=j):
                    c = list(stmt.find_all(exp.Case))[ci]
                    then_i = c.args["ifs"][bi].args["true"].copy()
                    c.args["ifs"][bi].set("true", c.args["ifs"][bj].args["true"].copy())
                    c.args["ifs"][bj].set("true", then_i)
                mutations.append((apply_swap_branches, desc))
        for branch_idx in range(len(ifs)):
            desc = f"Negate WHEN condition at branch {branch_idx} in CASE at index {case_idx}."
            def apply_negate(stmt, ci=case_idx, bi=branch_idx):
                c = list(stmt.find_all(exp.Case))[ci]
                cond = c.args["ifs"][bi].this
                new_cond = cond.this.copy() if isinstance(cond, exp.Not) else exp.Not(this=cond.copy())
                c.args["ifs"][bi].set("this", new_cond)
            mutations.append((apply_negate, desc))
    return mutations