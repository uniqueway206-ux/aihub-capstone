"""Natural-language -> SQL chat with defence in depth (Module 4: SQL database chat).

Safety layers: (1) prompt asks for one SELECT, (2) static validator, (3) read-only SQLite
connection, (4) row limit.
"""
import re
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from ..errors import UnsafeSQLError, ValidationError
from ..llm import text_of

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|truncate|vacuum)\b",
    re.IGNORECASE,
)


def clean_sql(raw: str) -> str:
    sql = re.sub(r"^```(?:sql)?|```$", "", raw.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    return sql.rstrip(";").strip()


def validate_select(sql: str) -> str:
    sql = clean_sql(sql)
    if not sql:
        raise UnsafeSQLError("Empty query.")
    if ";" in sql:
        raise UnsafeSQLError("Multiple statements are not allowed.")
    if "--" in sql or "/*" in sql:
        raise UnsafeSQLError("SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    if _FORBIDDEN.search(sql):
        raise UnsafeSQLError("Query contains a forbidden keyword.")
    return sql


class SQLChat:
    def __init__(self, llm, db_path: Path, row_limit: int = 50):
        self.llm = llm
        self.row_limit = row_limit
        if not Path(db_path).exists():
            raise ValidationError(
                f"Database {db_path} not found. Run: python scripts/seed_demo_db.py"
            )
        # mode=ro => the DB engine itself refuses writes, even if validation were bypassed
        self.engine = create_engine(f"sqlite:///file:{Path(db_path).resolve()}?mode=ro&uri=true")

    def schema(self) -> str:
        insp = inspect(self.engine)
        lines = []
        for table in insp.get_table_names():
            cols = ", ".join(f"{c['name']} {c['type']}" for c in insp.get_columns(table))
            lines.append(f"{table}({cols})")
        return "\n".join(lines)

    def run_sql(self, sql: str) -> tuple[list[str], list[list]]:
        sql = validate_select(sql)
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            cols = list(result.keys())
            rows = [list(r) for r in result.fetchmany(self.row_limit)]
        return cols, rows

    def ask(self, question: str) -> dict:
        gen = self.llm.invoke(
            "You write SQLite queries. Schema:\n"
            f"{self.schema()}\n\nReturn ONE read-only SELECT statement and nothing else.\n"
            f"Question: {question}"
        )
        sql = validate_select(text_of(gen))
        cols, rows = self.run_sql(sql)
        summary = text_of(
            self.llm.invoke(
                f"Question: {question}\nSQL: {sql}\nColumns: {cols}\nRows: {rows}\n"
                "Answer the question briefly in plain language using only these rows."
            )
        )
        return {"answer": summary, "sql": sql, "columns": cols, "rows": rows}
