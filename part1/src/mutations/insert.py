from sqlglot import exp
from typing import List, Tuple, Callable, Dict
from .common import collect_mutations_extreme_values, collect_mutations_relational_operators, collect_mutations_logical_operators, \
    collect_mutations_insert_unary_operator, collect_mutations_arithmetic_binary_operators, collect_mutations_between, \
    collect_mutations_like_patterns, collect_mutations_null_check
InsertMutation = Tuple[Callable[[exp.Insert], None], str]

def collect(statement: exp.Insert, schema: Dict[str, List[str]]) -> List[InsertMutation]:
    mutations: List[InsertMutation] = []
    # Here are mutations specific to the INSERT statement.
    mutations.extend(collect_mutations_conflict_resolution(statement))
    mutations.extend(collect_mutations_drop_values_row(statement))
    mutations.extend(collect_mutations_null_values(statement))
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

SQLITE_CONFLICT_ALTERNATIVES = ["IGNORE", "REPLACE", "ABORT", "FAIL", "ROLLBACK"]
def collect_mutations_conflict_resolution(statement: exp.Insert) -> List[InsertMutation]:
    mutations: List[InsertMutation] = []
    current = statement.args.get("alternative")
    for alt in SQLITE_CONFLICT_ALTERNATIVES:
        if alt == current:
            continue
        desc = f"Change INSERT conflict resolution to OR {alt}."
        mutations.append((lambda stmt, a=alt: stmt.set("alternative", a), desc))
    if current is not None:
        desc = "Remove INSERT conflict resolution clause."
        mutations.append((lambda stmt: stmt.set("alternative", None), desc))
    return mutations

def collect_mutations_drop_values_row(statement: exp.Insert) -> List[InsertMutation]:
    mutations: List[InsertMutation] = []
    values = statement.args.get("expression")
    if not isinstance(values, exp.Values):
        return mutations
    rows = values.expressions
    if len(rows) <= 1:
        return mutations
    for row_idx in range(len(rows)):
        desc = f"Drop VALUES row at index {row_idx}."
        def apply(stmt, ri=row_idx):
            stmt.args["expression"].args["expressions"].pop(ri)
        mutations.append((apply, desc))
    return mutations

def collect_mutations_null_values(statement: exp.Insert) -> List[InsertMutation]:
    mutations: List[InsertMutation] = []
    values = statement.args.get("expression")
    if not isinstance(values, exp.Values):
        return mutations
    for row_idx, row in enumerate(values.expressions):
        if not isinstance(row, exp.Tuple):
            continue
        for col_idx, val in enumerate(row.expressions):
            if isinstance(val, exp.Null):
                continue
            desc = f"Set INSERT value at row {row_idx}, column {col_idx} to NULL."
            def apply(stmt, ri=row_idx, ci=col_idx):
                stmt.args["expression"].expressions[ri].expressions[ci].replace(exp.Null())
            mutations.append((apply, desc))
    return mutations
