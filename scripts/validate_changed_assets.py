from __future__ import annotations
from datetime import datetime
from email import errors
import re
import subprocess
import sys
from pathlib import Path
import ast
import io
import tokenize

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*$")
OBJECT_NAME = r"`?[\w.-]+`?"

TABLE_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:EXTERNAL\s+)?TABLE\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?({OBJECT_NAME})",
    re.IGNORECASE,
)
VIEW_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+({OBJECT_NAME})",
    re.IGNORECASE,
)
PROCEDURE_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+({OBJECT_NAME})",
    re.IGNORECASE,
)
DATASET_RE = re.compile(
    r"\bCREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+([A-Za-z0-9_]+)",
    re.IGNORECASE,
)
COMMENTED_SQL_RE = re.compile(
    r"\b(?:"
    r"SELECT\s+.+?\s+FROM\b|"
    r"INSERT\s+INTO\b|"
    r"UPDATE\s+\S+\s+SET\b|"
    r"DELETE\s+FROM\b|"
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|PROCEDURE|FUNCTION)\b|"
    r"DROP\s+(?:TABLE|VIEW|PROCEDURE|FUNCTION)\b|"
    r"ALTER\s+TABLE\b|"
    r"MERGE\s+INTO\b|"
    r"TRUNCATE\s+TABLE\b|"
    r"CALL\s+[\w.`]+|"
    r"BEGIN\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

SQL_OBJECT = r"(?:`[^`]+`|[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){0,2})"

BACKUP_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:SNAPSHOT\s+)?TABLE\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?(?P<backup>{SQL_OBJECT})\s+"
    rf"(?:CLONE\s+(?P<clone>{SQL_OBJECT})|"
    rf"AS\s+SELECT\b.*?\bFROM\s+(?P<source>{SQL_OBJECT}))",
    re.IGNORECASE | re.DOTALL,
)

MUTATION_RE = re.compile(
    rf"^\s*(?P<operation>"
    rf"CREATE\s+OR\s+REPLACE\s+TABLE|"
    rf"UPDATE|DELETE\s+FROM|TRUNCATE\s+TABLE|INSERT(?:\s+INTO)?|"
    rf"MERGE\s+INTO|ALTER\s+TABLE"
    rf")\s+(?P<target>{SQL_OBJECT})",
    re.IGNORECASE,
)


def strip_sql_comments(sql: str) -> str:
    result: list[str] = []
    quote: str | None = None
    i = 0

    while i < len(sql):
        char = sql[i]

        if quote:
            result.append(char)
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 1
                else:
                    quote = None
            elif char == "\\" and i + 1 < len(sql):
                result.append(sql[i + 1])
                i += 1
        elif char in ("'", '"', "`"):
            quote = char
            result.append(char)
        elif sql.startswith("--", i):
            while i < len(sql) and sql[i] not in "\r\n":
                i += 1
            result.append(" ")
            continue
        elif sql.startswith("/*", i):
            i += 2
            while i < len(sql) and not sql.startswith("*/", i):
                if sql[i] in "\r\n":
                    result.append(sql[i])
                i += 1
            i += 2
            result.append(" ")
            continue
        else:
            result.append(char)

        i += 1

    return "".join(result)


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    start = 0
    quote: str | None = None
    i = 0

    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1
                else:
                    quote = None
            elif char == "\\":
                i += 1
        elif char in ("'", '"', "`"):
            quote = char
        elif char == ";":
            statement = sql[start:i].strip()
            if statement:
                statements.append(statement)
            start = i + 1
        i += 1

    statement = sql[start:].strip()
    if statement:
        statements.append(statement)

    return statements


def canonical_table_name(name: str) -> str:
    return name.strip("`").upper()


def normalize_sql(text: str) -> str:
    return text.translate(
        str.maketrans(
            {
                "\u00a0": " ",
                "\u2007": " ",
                "\u202f": " ",
            }
        )
    )


def object_parts(name: str) -> list[str]:
    return name.strip("`").split(".")


def find_matching_paren(text: str, opening: int) -> int | None:
    depth = 0
    quote: str | None = None
    i = opening

    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return None


def split_columns(text: str) -> list[str]:
    result: list[str] = []
    start = 0
    parens = 0
    angles = 0
    quote: str | None = None
    i = 0

    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
        elif char == "<":
            angles += 1
        elif char == ">":
            angles = max(0, angles - 1)
        elif char == "," and parens == 0 and angles == 0:
            result.append(text[start:i])
            start = i + 1
        i += 1

    result.append(text[start:])
    return result


def validate_dataset(path: Path, sql: str, errors: list[str]) -> None:
    match = DATASET_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE SCHEMA IF NOT EXISTS")
        return

    name = match.group(1)
    if name != path.stem or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: dataset name must be uppercase and match {path.stem}")

    options = sql[match.end() :]
    if not re.search(r"\blocation\s*=\s*['\"]us-central1['\"]", options, re.I):
        errors.append(f"{path}: dataset location must be us-central1")
    if not re.search(r"\bdescription\s*=\s*['\"][^'\"]+['\"]", options, re.I):
        errors.append(f"{path}: dataset description is required")


def validate_table(path: Path, sql: str, errors: list[str]) -> None:
    match = TABLE_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE TABLE")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    if name != path.stem or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: table name must be uppercase and match {path.stem}")
    if len(parts) >= 2 and parts[-2] != path.parts[-3]:
        errors.append(f"{path}: SQL dataset must match its directory {path.parts[-3]}")
    if re.search(r"\bCREATE\s+OR\s+REPLACE\s+TABLE\b", match.group(0), re.I):
        errors.append(f"{path}: CREATE OR REPLACE TABLE can overwrite data; use a reviewed migration")

    opening = sql.find("(", match.end())
    closing = find_matching_paren(sql, opening) if opening >= 0 else None
    if closing is None:
        errors.append(f"{path}: could not parse table columns")
        return

    for column in split_columns(sql[opening + 1 : closing]):
        column = column.strip()
        column_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+", column)
        if not column_match:
            errors.append(f"{path}: could not parse column {column[:50]!r}")
            continue

        column_name = column_match.group(1)
        if not IDENTIFIER.fullmatch(column_name):
            errors.append(f"{path}: column {column_name} must be uppercase")
        if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", column, re.I | re.S):
            errors.append(f"{path}: column {column_name} requires a description")

    if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", sql[closing + 1 :], re.I | re.S):
        errors.append(f"{path}: table description is required")


def validate_view(path: Path, sql: str, errors: list[str]) -> None:
    match = VIEW_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE VIEW")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    folder_dataset = path.parts[-3]
    expected_dataset = f"{folder_dataset}_V"

    if len(parts) < 2 or parts[-2] != expected_dataset:
        errors.append(
            f"{path}: view SQL dataset must be {expected_dataset} "
            f"for the {folder_dataset} folder"
        )
    if (
        not name.endswith("_V")
        or name != path.stem
        or not IDENTIFIER.fullmatch(name)
    ):
        errors.append(
            f"{path}: view name must be uppercase, end in _V, "
            "and match the filename"
        )
    if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", sql, re.I | re.S):
        errors.append(f"{path}: view description is required")


def validate_routine(path: Path, sql: str, errors: list[str]) -> None:
    match = PROCEDURE_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE PROCEDURE")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    dataset = path.parts[-3]

    if not name.startswith("SP_") or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: procedure name must be uppercase and start with SP_")
    if name != path.stem:
        errors.append(f"{path}: procedure name must match filename {path.stem}")
    if len(parts) < 2 or parts[-2] != dataset:
        errors.append(f"{path}: procedure SQL dataset must match directory {dataset}")

    comments = re.findall(r"--[^\r\n]*|/\*.*?\*/", sql, re.S)
    for comment in comments:
        comment_text = re.sub(r"^(?:--|/\*|\*/|\*)", "", comment, flags=re.M).strip()
        if COMMENTED_SQL_RE.search(comment_text):
            errors.append(f"{path}: commented-out SQL code is not allowed")
            break

def validate_dml(path: Path, sql: str, errors: list[str]) -> None:
    relative = path.relative_to(ROOT)
    parts = relative.parts

    if len(parts) != 4 or parts[0:2] != ("BigQuery", "DML"):
        errors.append(
            f"{relative}: DML files must be located at "
            "BigQuery/DML/MMDDYYYY/<file>.sql"
        )
        return

    folder_date = parts[2]
    if not re.fullmatch(r"\d{8}", folder_date):
        errors.append(
            f"{relative}: DML folder must use MMDDYYYY, for example 10182026"
        )
        return

    try:
        datetime.strptime(folder_date, "%m%d%Y")
    except ValueError:
        errors.append(
            f"{relative}: {folder_date} is not a valid calendar date in MMDDYYYY format"
        )
        return

    statements = split_sql_statements(strip_sql_comments(sql))
    backups: list[tuple[str, str]] = []
    used_backups: set[int] = set()
    mutation_count = 0
    last_phase = 0

    for statement in statements:
        backup_match = BACKUP_RE.search(statement)
        if backup_match:
            backup_name = canonical_table_name(backup_match.group("backup"))
            source_name = canonical_table_name(
                backup_match.group("clone") or backup_match.group("source")
            )
            backup_parts = backup_name.split(".")
            backup_table = backup_parts[-1]

            if len(backup_parts) < 2 or backup_parts[-2] != "DP_BASE_BACKUP":
                errors.append(
                    f"{relative}: backup table {backup_name} must be in DP_BASE_BACKUP"
                )
            if last_phase > 0:
                errors.append(
                    f"{relative}: backup statements must come before all mutations"
                )
                continue

            if not re.fullmatch(r"[A-Z][A-Z0-9_]*_BKP_[A-Z0-9_-]+", backup_table):
                errors.append(
                    f"{relative}: backup table must follow "
                    "DP_BASE_BACKUP.<TABLE_NAME>_BKP_<DATE>"
                )
                continue

            backups.append((backup_name, source_name))
            continue

        mutation_match = MUTATION_RE.match(statement)
        if not mutation_match:
            continue

        mutation_count += 1
        operation = " ".join(mutation_match.group("operation").upper().split())

        if operation in {"CREATE OR REPLACE TABLE", "ALTER TABLE"}:
            phase = 1
        elif operation in {"TRUNCATE TABLE", "DELETE FROM"}:
            phase = 2
        elif operation.startswith("INSERT"):
            phase = 3
        elif operation in {"UPDATE", "MERGE INTO"}:
            phase = 4
        else:
            errors.append(f"{relative}: unsupported mutation {operation}")
            continue

        if phase < last_phase:
            errors.append(
                f"{relative}: {operation} is out of order; expected "
                "backup -> CREATE OR REPLACE/ALTER -> TRUNCATE/DELETE "
                "-> INSERT -> UPDATE/MERGE"
            )
        last_phase = max(last_phase, phase)
        target_name = canonical_table_name(mutation_match.group("target"))
        target_table = target_name.split(".")[-1]
        matching_backup_index: int | None = None

        for index, (backup_name, source_name) in enumerate(backups):
            backup_table = backup_name.split(".")[-1]
            if (
                index not in used_backups
                and source_name == target_name
                and backup_table.startswith(f"{target_table}_BKP_")
            ):
                matching_backup_index = index
                break

        if matching_backup_index is None:
            errors.append(
                f"{relative}: {operation} on {target_name} requires a preceding "
                "backup in DP_BASE_BACKUP, named "
                f"{target_table}_BKP_<DATE>, created from that same target"
            )
        else:
            used_backups.add(matching_backup_index)

    if mutation_count == 0:
        errors.append(
            f"{relative}: no supported DML/DDL mutation found "
            "(UPDATE, DELETE, TRUNCATE, INSERT, MERGE, or ALTER)"
        )
def dag_target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for item in node.elts:
            names.extend(dag_target_names(item))
        return names
    return []


def dag_call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def validate_dag_file(path: Path, errors: list[str]) -> None:
    relative = path.relative_to(ROOT)

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(relative))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        errors.append(f"{relative}: Python syntax/indentation error: {exc}")
        return

    for line_number, line in enumerate(source.splitlines(), start=1):
        indentation = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in indentation:
            errors.append(
                f"{relative}:{line_number}: indentation must use spaces, not tabs"
            )
        elif len(indentation) % 4:
            errors.append(
                f"{relative}:{line_number}: indentation must use multiples of 4 spaces"
            )

    constants: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.target.id] = node.value.value

    def string_value(node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return constants.get(node.id)
        return None

    def validate_dag_id(call: ast.Call, function_name: str | None = None) -> None:
        dag_id_node = next(
            (keyword.value for keyword in call.keywords if keyword.arg == "dag_id"),
            None,
        )

        call_name = dag_call_name(call.func)
        if dag_id_node is None and call_name == "DAG" and call.args:
            dag_id_node = call.args[0]

        dag_id = string_value(dag_id_node) if dag_id_node is not None else function_name

        if dag_id is None:
            errors.append(
                f"{relative}:{call.lineno}: DAG ID must be a string literal "
                "or a string constant so the dag_ prefix can be checked"
            )
        elif not dag_id.startswith("dag_"):
            errors.append(
                f"{relative}:{call.lineno}: DAG ID {dag_id!r} must start with 'dag_'"
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                context = item.context_expr
                if isinstance(context, ast.Call) and dag_call_name(context.func) == "DAG":
                    validate_dag_id(context)
                    if item.optional_vars is not None:
                        for name in dag_target_names(item.optional_vars):
                            if not name.startswith("dag_"):
                                errors.append(
                                    f"{relative}:{node.lineno}: DAG variable "
                                    f"{name!r} must start with 'dag_'"
                                )

        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if isinstance(value, ast.Call) and dag_call_name(value.func) == "DAG":
                validate_dag_id(value)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for name in dag_target_names(target):
                        if not name.startswith("dag_"):
                            errors.append(
                                f"{relative}:{node.lineno}: DAG variable "
                                f"{name!r} must start with 'dag_'"
                            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                decorator_call = decorator if isinstance(decorator, ast.Call) else None
                decorator_func = (
                    decorator_call.func if decorator_call is not None else decorator
                )
                if dag_call_name(decorator_func) == "dag":
                    if not node.name.startswith("dag_"):
                        errors.append(
                            f"{relative}:{node.lineno}: DAG function "
                            f"{node.name!r} must start with 'dag_'"
                        )
                    if decorator_call is not None:
                        validate_dag_id(decorator_call, function_name=node.name)

    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.INDENT:
                if "\t" in token.string or len(token.string) % 4:
                    errors.append(
                        f"{relative}:{token.start[0]}: block indentation must use "
                        "multiples of 4 spaces"
                    )

            if token.type == tokenize.COMMENT:
                comment = token.string[1:].strip()
                if not re.fullmatch(r"[A-Za-z][A-Za-z ,'-]*[.!?]", comment):
                    errors.append(
                        f"{relative}:{token.start[0]}: comments must be one plain "
                        "English sentence; commented-out code is not allowed"
                    )
    except (tokenize.TokenError, IndentationError) as exc:
        errors.append(f"{relative}: tokenization/indentation error: {exc}")

def changed_files(base: str, head: str) -> list[Path]:
    if re.fullmatch(r"0+", base):
        raise ValueError("The base commit is unavailable; merge a follow-up commit to run this validation.")

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base}...{head}",
            "--",
            "BigQuery",
            "DataProc",
            "Composer/dags",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / name for name in result.stdout.splitlines()]

def report_validated(relative: Path, asset_type: str) -> None:
    message = f"{relative} ({asset_type}) validated and meets expected standards."
    print(f"✅ {message}")
    print(f"::notice title=Standards validation passed::{message}")

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_changed_assets.py BASE_SHA HEAD_SHA", file=sys.stderr)
        return 2

    try:
        files = changed_files(sys.argv[1], sys.argv[2])
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Could not determine changed files: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    validated = 0

    for path in files:
        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)
        if path.suffix == ".py":
            error_count = len(errors)

            if relative.parts[:2] == ("Composer", "dags"):
                validate_dag_file(path, errors)
                asset_type = "Airflow DAG"
            else:
                try:
                    compile(path.read_text(encoding="utf-8"), str(relative), "exec")
                except (SyntaxError, UnicodeDecodeError) as exc:
                    errors.append(f"{relative}: Python validation failed: {exc}")
                asset_type = "Python"

            if len(errors) == error_count:
                report_validated(relative, asset_type)
            validated += 1
            continue

        if path.suffix != ".sql" or relative.parts[0] != "BigQuery":
            continue

        sql = normalize_sql(path.read_text(encoding="utf-8-sig"))
        parts = relative.parts
        error_count = len(errors)
        asset_type = "BigQuery SQL"

        if len(parts) == 3 and parts[1] == "DATASETS":
            validate_dataset(path, sql, errors)
            asset_type = "BigQuery dataset"
        elif len(parts) == 4 and parts[2] == "TABLES":
            validate_table(path, sql, errors)
            asset_type = "BigQuery table"
        elif len(parts) == 4 and parts[2] == "VIEWS":
            validate_view(path, sql, errors)
            asset_type = "BigQuery view"
        elif len(parts) == 4 and parts[2] == "ROUTINES":
            validate_routine(path, sql, errors)
            asset_type = "BigQuery routine"
        elif len(parts) == 4 and parts[1] == "DML":
            asset_type = "BigQuery DML"
        else:
            errors.append(
                f"{relative}: SQL file is not in a recognized BigQuery asset directory"
            )

        if len(errors) == error_count:
            report_validated(relative, asset_type)
        validated += 1

    if errors:
        print("Changed-file validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Changed-file validation passed ({validated} changed files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())