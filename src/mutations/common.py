from sqlglot import exp
from typing import List, Tuple, Callable, Dict

StatementMutation = Tuple[Callable[[exp.Expr], None], str]

################################### Mutations for any kind of statement ###################################
EXTREME_NUMBERS = [0, 1, -1, 2**31-1, -2**31, 2**63-1, -2**63]
EXTREME_STRINGS = [""]
def collect_mutations_extreme_values(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 1: Replace literals with extreme values (both numbers and strings).
    mutations: List[StatementMutation] = []
    num_literals = [n for n in statement.find_all(exp.Literal) if n.is_number]
    for target_idx, literal in enumerate(num_literals):
        for extreme in EXTREME_NUMBERS:
            if str(extreme) == literal.name:
                continue
            desc = f"Replace numeric literal at index {target_idx} with {extreme}."
            def apply_numeric(stmt, ti=target_idx, v=extreme):
                lits = [n for n in stmt.find_all(exp.Literal) if n.is_number]
                lits[ti].replace(exp.Literal.number(v))
            mutations.append((apply_numeric, desc))
    str_literals = [n for n in statement.find_all(exp.Literal) if n.is_string]
    for target_idx, literal in enumerate(str_literals):
        for extreme in EXTREME_STRINGS:
            if extreme == literal.name:
                continue
            safe_str = extreme if len(extreme) <= 20 else f"<Long String: {len(extreme)} chars>"
            desc = f"Replace string literal at index {target_idx} with {safe_str}."
            def apply_string(stmt, ti=target_idx, v=extreme):
                lits = [n for n in stmt.find_all(exp.Literal) if n.is_string]
                lits[ti].replace(exp.Literal.string(v))
            mutations.append((apply_string, desc))
    return mutations

RELATIONAL_OPERATORS = [exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE]
def collect_mutations_relational_operators(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 2: Replace a relational operator (=, <>, <, <=, >, >=).
    targets = list(statement.find_all(*RELATIONAL_OPERATORS))
    mutations: List[StatementMutation] = []
    for target_idx, target in enumerate(targets):
        for choice in [op for op in RELATIONAL_OPERATORS if not isinstance(target, op)] + ["falseop", "trueop"]:
            choice_name = choice if isinstance(choice, str) else choice.__name__
            desc = f"Replace relational operator at index {target_idx} with {choice_name}."
            def apply(stmt, ti=target_idx, c=choice):
                mutate_relational_operator(list(stmt.find_all(*RELATIONAL_OPERATORS))[ti], c)
            mutations.append((apply, desc))
    return mutations

def mutate_relational_operator(target: exp.EQ | exp.NEQ | exp.LT | exp.LTE | exp.GT | exp.GTE, choice):
    if choice == "falseop":
        target.replace(exp.false())
    elif choice == "trueop":
        target.replace(exp.true())
    else:
        target.replace(choice(this=target.left.copy(), expression=target.right.copy()))

LOGICAL_OPERATORS = [exp.And, exp.Or]
def collect_mutations_logical_operators(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 3: Replace a logical operator (AND, OR).
    targets = list(statement.find_all(*LOGICAL_OPERATORS))
    mutations: List[StatementMutation] = []
    for target_idx, target in enumerate(targets):
        for choice in [exp.Or if isinstance(target, exp.And) else exp.And, "falseop", "trueop", "leftop", "rightop"]:
            choice_name = choice if isinstance(choice, str) else choice.__name__
            desc = f"Replace logical operator at index {target_idx} with {choice_name}."
            def apply(stmt, ti=target_idx, c=choice):
                mutate_logical_operator(list(stmt.find_all(*LOGICAL_OPERATORS))[ti], c)
            mutations.append((apply, desc))
    return mutations

def mutate_logical_operator(target: exp.And | exp.Or, choice):
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

def collect_mutations_insert_unary_operator(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 4: Insert a unary operator (+1, -1, negate, abs, sin, log2).
    expr_to_mutate = [exp.Literal, exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod]
    targets = [t for t in statement.find_all(*expr_to_mutate)
             if not (isinstance(t, exp.Literal) and t.is_string)]
    mutations: List[StatementMutation] = []
    for target_idx in range(len(targets)):
        for choice in ["negate", "add1", "sub1", "abs", "-abs", "sin", "log2"]:
            desc = f"Apply {choice} to arithmetic expression at index {target_idx}."
            mutations.append((
                lambda stmt, ti=target_idx, c=choice:
                    mutate_insert_unary_operator([t for t in stmt.find_all(*expr_to_mutate)
                                                  if not (isinstance(t, exp.Literal) and t.is_string)][ti], c), desc))
    return mutations

def mutate_insert_unary_operator(target: exp.Expr, choice: str):
    if choice == "negate":
        target.replace(exp.Neg(this=target.copy()))
    elif choice == "add1":
        target.replace(exp.Add(this=target.copy(), expression=exp.Literal.number(1)))
    elif choice == "sub1":
        target.replace(exp.Sub(this=target.copy(), expression=exp.Literal.number(1)))
    elif choice == "abs":
        target.replace(exp.Abs(this=target.copy()))
    elif choice == "-abs":
        target.replace(exp.Neg(this=exp.Abs(this=target.copy())))
    elif choice == "sin":
        target.replace(exp.Sin(this=target.copy()))
    elif choice == "log2":
        target.replace(exp.Anonymous(this="LOG2", expressions=[target.copy()]))

def collect_mutations_arithmetic_binary_operators(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 5: Replace an arithmetic binar operator (+, -, *, /, %).
    arithmetic_operators = [exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod]
    targets = list(statement.find_all(*arithmetic_operators))
    mutations: List[StatementMutation] = []
    for target_idx, target in enumerate(targets):
        for choice in [op for op in arithmetic_operators if not isinstance(target, op)] + ["leftop", "rightop"]:
            choice_name = choice if isinstance(choice, str) else choice.__name__
            desc = f"Replace arithmetic operator at index {target_idx} with {choice_name}."
            def apply(stmt, ti=target_idx, c=choice, ops=arithmetic_operators):
                mutate_binary_arithmetic_operator(list(stmt.find_all(*ops))[ti], c)
            mutations.append((apply, desc))
    return mutations

def mutate_binary_arithmetic_operator(target: exp.Add | exp.Sub | exp.Mul | exp.Div | exp.Mod, choice):
    if choice == "leftop":
        target.replace(target.left.copy())
    elif choice == "rightop":
        target.replace(target.right.copy())
    else:
        target.replace(choice(this=target.left.copy(), expression=target.right.copy()))

def collect_mutations_between(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 6: Replace BETWEEN with explicit inequalities.
    targets = list(statement.find_all(exp.Between))
    if not targets:
        return []
    mutations: List[StatementMutation] = []
    for target_idx in range(len(targets)):
        for choice in [1, 2]:
            desc = f"Replace BETWEEN at index {target_idx} with explicit inequalities (Option {choice})."
            mutations.append((
                lambda stmt, ti=target_idx, c=choice:
                    mutate_between(list(stmt.find_all(exp.Between))[ti], c), desc))
    return mutations

def mutate_between(target: exp.Between, choice: int):
    a, x, y = target.this.copy(), target.args["low"].copy(), target.args["high"].copy()
    if choice == 1:
        cond = exp.And(this=exp.GT(this=a.copy(), expression=x), expression=exp.LTE(this=a.copy(), expression=y))
    else:
        cond = exp.And(this=exp.GTE(this=a.copy(), expression=x), expression=exp.LT(this=a.copy(), expression=y))
    if isinstance(target.parent, exp.Not):
        target.parent.replace(exp.Not(this=cond))
    else:
        target.replace(cond)

def collect_mutations_like_patterns(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 7: Mutate a LIKE/ILIKE wildcard pattern.
    all_targets = list(statement.find_all(exp.Like, exp.ILike))
    valid_targets = [t for t in all_targets if isinstance(t.expression, exp.Literal) and t.expression.is_string]
    mutations: List[StatementMutation] = []
    for target_idx, target in enumerate(valid_targets):
        pattern = target.expression.name
        if not pattern:
            continue
        new_patterns: set = set()
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
        for new_pattern in sorted(new_patterns):
            desc = f"Mutate LIKE pattern at index {target_idx} from '{pattern}' to '{new_pattern}'."
            def apply(stmt, ti=target_idx, np=new_pattern):
                all_copy = list(stmt.find_all(exp.Like, exp.ILike))
                valid_copy = [t for t in all_copy if isinstance(t.expression, exp.Literal) and t.expression.is_string]
                valid_copy[ti].expression.set("this", np)
            mutations.append((apply, desc))
    return mutations

def collect_mutations_null_check(statement: exp.Expr) -> List[StatementMutation]:
    # Mutation 8: Replace a relational operator with IS NULL / IS NOT NULL.
    targets = list(statement.find_all(*RELATIONAL_OPERATORS))
    mutations: List[StatementMutation] = []
    for target_idx, target in enumerate(targets):
        col = target.left if isinstance(target.left, exp.Column) else \
              target.right if isinstance(target.right, exp.Column) else None
        if col is None:
            continue
        for is_not in [False, True]:
            null_str = "IS NOT NULL" if is_not else "IS NULL"
            desc = f"Replace comparison at index {target_idx} with {null_str}."
            def apply(stmt, ti=target_idx, n=is_not, ct=RELATIONAL_OPERATORS):
                targets_copy = list(stmt.find_all(*RELATIONAL_OPERATORS))
                copy = targets_copy[ti]
                col_copy = copy.left if isinstance(copy.left, exp.Column) else copy.right
                mutate_null_check(copy, col_copy, n)
            mutations.append((apply, desc))
    return mutations

def mutate_null_check(target: exp.Expr, col: exp.Column, is_not: bool):
    null_check = exp.Is(this=col.copy(), expression=exp.Null())
    target.replace(exp.Not(this=null_check) if is_not else null_check)