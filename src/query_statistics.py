from src.executor import ExecutionResult

class QueryStatistics:
    KEYWORDS = [
        "ABORT",
        "ACTION",
        "ADD",
        "AFTER",
        "ALL",
        "ALTER",
        "ALWAYS",
        "ANALYZE",
        "AND",
        "AS",
        "ASC",
        "ATTACH",
        "AUTOINCREMENT",
        "BEFORE",
        "BEGIN",
        "BETWEEN",
        "BY",
        "CASCADE",
        "CASE",
        "CAST",
        "CHECK",
        "COLLATE",
        "COLUMN",
        "COMMIT",
        "CONFLICT",
        "CONSTRAINT",
        "CREATE",
        "CROSS",
        "CURRENT",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "DATABASE",
        "DEFAULT",
        "DEFERRABLE",
        "DEFERRED",
        "DELETE",
        "DESC",
        "DETACH",
        "DISTINCT",
        "DO",
        "DROP",
        "EACH",
        "ELSE",
        "END",
        "ESCAPE",
        "EXCEPT",
        "EXCLUDE",
        "EXCLUSIVE",
        "EXISTS",
        "EXPLAIN",
        "FAIL",
        "FILTER",
        "FIRST",
        "FOLLOWING",
        "FOR",
        "FOREIGN",
        "FROM",
        "FULL",
        "GENERATED",
        "GLOB",
        "GROUP",
        "GROUPS",
        "HAVING",
        "IF",
        "IGNORE",
        "IMMEDIATE",
        "IN",
        "INDEX",
        "INDEXED",
        "INITIALLY",
        "INNER",
        "INSERT",
        "INSTEAD",
        "INTERSECT",
        "INTO",
        "IS",
        "ISNULL",
        "JOIN",
        "KEY",
        "LAST",
        "LEFT",
        "LIKE",
        "LIMIT",
        "MATCH",
        "MATERIALIZED",
        "NATURAL",
        "NO",
        "NOT",
        "NOTHING",
        "NOTNULL",
        "NULL",
        "NULLS",
        "OF",
        "OFFSET",
        "ON",
        "OR",
        "ORDER",
        "OTHERS",
        "OUTER",
        "OVER",
        "PARTITION",
        "PLAN",
        "PRAGMA",
        "PRECEDING",
        "PRIMARY",
        "QUERY",
        "RAISE",
        "RANGE",
        "RECURSIVE",
        "REFERENCES",
        "REGEXP",
        "REINDEX",
        "RELEASE",
        "RENAME",
        "REPLACE",
        "RESTRICT",
        "RETURNING",
        "RIGHT",
        "ROLLBACK",
        "ROW",
        "ROWS",
        "SAVEPOINT",
        "SELECT",
        "SET",
        "TABLE",
        "TEMP",
        "TEMPORARY",
        "THEN",
        "TIES",
        "TO",
        "TRANSACTION",
        "TRIGGER",
        "UNBOUNDED",
        "UNION",
        "UNIQUE",
        "UPDATE",
        "USING",
        "VACUUM",
        "VALUES",
        "VIEW",
        "VIRTUAL",
        "WHEN",
        "WHERE",
        "WINDOW",
        "WITH",
        "WITHOUT"
    ]
    
    def __init__(self):
        self.total_queries = 0
        self.original_errors = 0
        self.patched_errors = 0
        self.logical_bugs = 0
        self.successes = 0
        self.timeouts = 0
        
    
    def collect(self, result: ExecutionResult) -> None:
        self.total_queries += 1
        if result["status"] == "ORIGINAL_ERROR":
            self.original_errors += 1
        elif result["status"] == "PATCHED_ERROR":
            self.patched_errors += 1
        elif result["status"] == "LOGICAL_BUG":
            self.logical_bugs += 1
        elif result["status"] == "SUCCESS":
            self.successes += 1
        elif result["status"] == "TIMEOUT":
            self.timeouts += 1
        
    
    def get_query_keywords(self, query: str) -> set[str]:
        words = set(query.split())
        return words.intersection(set(self.KEYWORDS))
    
    
    def get_keyword_stats(self, queries: list[str]) -> dict[str, int]:
        keyword_counts: dict[str, int] = {keyword: 0 for keyword in self.KEYWORDS}
        for query in queries:
            keywords_in_query = self.get_query_keywords(query)
            for keyword in keywords_in_query:
                keyword_counts[keyword] += 1
        return keyword_counts

    
    def get_top30_keywords_stats(self, keyword_counts: dict[str, int]) -> str:
        sorted_keywords = sorted(keyword_counts.items(), key=lambda item: item[1], reverse=True)
        top30 = sorted_keywords[:30]
        
        result = "Top 30 SQL keywords and number of queries they appear in:\n"
        for keyword, count in top30:
            result += f"{keyword}: {count}\n"
        return result

    def get_validity_stats(self) -> str:        
        error_rate = (self.original_errors / self.total_queries) * 100 if self.total_queries > 0 else 0
        return f"Query validity stats: {self.total_queries} queries executed, {self.original_errors} errors, Error rate: {error_rate:.2f}%"
