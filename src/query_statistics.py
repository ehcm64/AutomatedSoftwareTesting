from src.executor import ExecutionResult

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

class QueryStatistics:
    def __init__(self):
        self.queries_generated = 0
        self.successes = 0
        self.unexpected_errors = 0
        self.logical_bugs = 0
        self.crashes = 0
        self.invalids = 0
        self.timeouts = 0
        
    
    def collect(self, result: ExecutionResult) -> None:
        self.queries_generated += 1
        if result["status"] == "SUCCESS": self.successes += 1
        elif result["status"] == "UNEXPECTED_ERROR": self.unexpected_errors += 1
        elif result["status"] == "LOGICAL_BUG": self.logical_bugs += 1
        elif result["status"] == "CRASH": self.crashes += 1
        elif result["status"] == "INVALID": self.invalids += 1
        elif result["status"] == "TIMEOUT": self.timeouts += 1
         
    @staticmethod
    def get_query_keywords(query: str) -> set[str]:
        words = set(query.split())
        return words.intersection(set(KEYWORDS))
    
    @staticmethod
    def get_keyword_stats(queries: list[str]) -> dict[str, int]:
        keyword_counts: dict[str, int] = {keyword: 0 for keyword in KEYWORDS}
        for query in queries:
            keywords_in_query = QueryStatistics.get_query_keywords(query)
            for keyword in keywords_in_query:
                keyword_counts[keyword] += 1
        return keyword_counts

    @staticmethod
    def get_top30_keywords_stats(queries: list[str]) -> str:
        keyword_counts = QueryStatistics.get_keyword_stats(queries)
        sorted_keywords = sorted(keyword_counts.items(), key=lambda item: item[1], reverse=True)
        top30 = sorted_keywords[:30]
        
        result = "Top 30 SQL keywords and number of queries they appear in:\n"
        for keyword, count in top30:
            result += f"{keyword}: {count}\n"
        return result


    @staticmethod
    def get_average_keyword_frequencies(queries: list[str]) -> dict[str, float]:
        counts = {keyword: 0 for keyword in KEYWORDS}
        for query in queries:
            words = query.split()
            for word in words:
                if word in counts:
                    counts[word] += 1
                    
        sorted_keywords = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        top30 = sorted_keywords[:30]

        result = "Top 30 SQL keywords average frequencies:\n"
        total_queries = len(queries)
        for keyword, count in top30:
            result += f"{keyword}: {(count / total_queries):.2f}\n"

        return result


    def get_validity_stats(self) -> str:        
        error_rate = (self.invalids / self.queries_generated) * 100 if self.queries_generated > 0 else 0
        return f"Query validity stats: {self.queries_generated} queries executed, {self.successes} errors, Error rate: {error_rate:.2f}%"
