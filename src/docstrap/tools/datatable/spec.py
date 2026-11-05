"""The table file: what a ``docstrap-datatable`` directive reads.

One JSON object beside the page, holding the columns and the rows::

    {
      "columns": [
        {"key": "id", "label": "Task", "type": "link", "href": "page"},
        {"key": "filed", "label": "Filed", "type": "date"},
        {"key": "state", "label": "State", "type": "enum", "filterable": true,
         "values": ["queued", "held", "blocked", "in_flight"]},
        {"key": "work", "label": "Work", "type": "symbol", "filterable": true,
         "symbols": {"code": "🔨", "docs": "📝"}}
      ],
      "rows": [
        {"id": "fm-1", "page": "tasks/fm-1", "filed": "2026-10-01",
         "state": "queued", "work": "code"}
      ]
    }

Everything here is checked when the page builds, and a file that does
not match is refused with the JSON path of what is wrong. A table that
half-renders a malformed file would show a reader a table that is wrong
without saying so; a build error names the file and the field.

This module reads and checks. It knows nothing of Sphinx, of HTML or of
pages, so it is tested as plain data; ``views.py`` renders what it
returns, and the client sorts and filters it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The column types, in the order the docs list them.
COLUMN_TYPES: tuple[str, ...] = ("text", "date", "enum", "symbol", "link")

#: A date cell: a calendar day, optionally followed by a time. Compared
#: as a string, which orders ISO dates correctly and needs no parsing.
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ].*)?$")

_TOP_KEYS = frozenset({"columns", "rows"})
_COLUMN_KEYS = frozenset(
    {"key", "label", "type", "sortable", "filterable", "values", "symbols", "href"}
)

#: What a cell may hold. A list is for a cell carrying several values —
#: a task's duplicates — and is shown joined and filtered by membership.
_SCALARS = (str, int, float, bool, type(None))


class TableError(ValueError):
    """The table file is not a table this tool can show."""


@dataclass(frozen=True, slots=True)
class Column:
    """One column, as the file declared it with its defaults filled in."""

    key: str
    label: str
    type: str
    sortable: bool = True
    filterable: bool = False
    #: Enum and symbol columns: the order values sort and are offered in.
    #: Values not listed sort after these, alphabetically.
    values: tuple[str, ...] | None = None
    #: Symbol columns: what each value is shown as.
    symbols: dict[str, str] | None = None
    #: Link columns: the row field holding the target, when the cell's
    #: own value is the text and not the target.
    href: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """The column as the client receives it. Absent options are omitted."""
        payload: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "sortable": self.sortable,
            "filterable": self.filterable,
        }
        if self.values is not None:
            payload["values"] = list(self.values)
        if self.symbols is not None:
            payload["symbols"] = dict(self.symbols)
        return payload


@dataclass(frozen=True, slots=True)
class Table:
    columns: tuple[Column, ...]
    #: In the file's order, which is the order the table first shows.
    rows: tuple[dict[str, Any], ...]


def load(path: Path) -> Table:
    """Read and check the table file at ``path``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TableError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TableError(f"{path} is not JSON: {exc}") from exc
    return parse(data)


def parse(data: Any) -> Table:
    """Check a decoded table file and return it with defaults filled in."""
    if not isinstance(data, dict):
        raise TableError("the table file must be a JSON object")
    _no_unknown_keys(data, _TOP_KEYS, "the table file")

    raw_columns = data.get("columns")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise TableError("columns: must be a non-empty list")
    columns = tuple(_column(raw, f"columns[{i}]") for i, raw in enumerate(raw_columns))
    seen: set[str] = set()
    for i, column in enumerate(columns):
        if column.key in seen:
            raise TableError(f"columns[{i}].key: {column.key!r} is declared twice")
        seen.add(column.key)

    raw_rows = data.get("rows")
    if not isinstance(raw_rows, list):
        raise TableError("rows: must be a list")
    rows = tuple(_row(raw, f"rows[{i}]", columns) for i, raw in enumerate(raw_rows))
    return Table(columns=columns, rows=rows)


def _no_unknown_keys(obj: dict[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise TableError(
            f"{where}: unknown key{'s' if len(unknown) > 1 else ''} "
            f"{', '.join(repr(k) for k in unknown)}; "
            f"allowed: {', '.join(sorted(allowed))}"
        )


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise TableError(f"{where}: must be a non-empty string")
    return value


def _flag(obj: dict[str, Any], name: str, default: bool, where: str) -> bool:
    value = obj.get(name, default)
    if not isinstance(value, bool):
        raise TableError(f"{where}.{name}: must be true or false")
    return value


def _column(raw: Any, where: str) -> Column:
    if not isinstance(raw, dict):
        raise TableError(f"{where}: must be an object")
    _no_unknown_keys(raw, _COLUMN_KEYS, where)

    key = _string(raw.get("key"), f"{where}.key")
    label = _string(raw.get("label", key), f"{where}.label")
    kind = raw.get("type")
    if kind not in COLUMN_TYPES:
        raise TableError(
            f"{where}.type: {kind!r} is not one of {', '.join(COLUMN_TYPES)}"
        )

    values = None
    if "values" in raw:
        if kind not in ("enum", "symbol"):
            raise TableError(f"{where}.values: only an enum or symbol column has values")
        listed = raw["values"]
        if not isinstance(listed, list) or not all(isinstance(v, str) for v in listed):
            raise TableError(f"{where}.values: must be a list of strings")
        values = tuple(listed)

    symbols = None
    if kind == "symbol":
        mapping = raw.get("symbols")
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
        ):
            raise TableError(
                f"{where}.symbols: a symbol column needs an object mapping each "
                f"value to the symbol shown for it"
            )
        symbols = dict(mapping)
    elif "symbols" in raw:
        raise TableError(f"{where}.symbols: only a symbol column has symbols")

    href = None
    if "href" in raw:
        if kind != "link":
            raise TableError(f"{where}.href: only a link column has href")
        href = _string(raw["href"], f"{where}.href")

    return Column(
        key=key,
        label=label,
        type=kind,
        sortable=_flag(raw, "sortable", True, where),
        filterable=_flag(raw, "filterable", False, where),
        values=values,
        symbols=symbols,
        href=href,
    )


def _row(raw: Any, where: str, columns: tuple[Column, ...]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TableError(f"{where}: must be an object")
    for key, value in raw.items():
        if isinstance(value, list):
            if not all(isinstance(v, _SCALARS) and v is not None for v in value):
                raise TableError(
                    f"{where}.{key}: a list cell holds strings, numbers or booleans"
                )
        elif not isinstance(value, _SCALARS):
            raise TableError(
                f"{where}.{key}: a cell is a string, number, boolean, null or a "
                f"list of those"
            )
    for column in columns:
        value = raw.get(column.key)
        if column.type == "date" and value is not None:
            if not isinstance(value, str) or not _DATE.match(value):
                raise TableError(
                    f"{where}.{column.key}: {value!r} is not a YYYY-MM-DD date"
                )
        if column.type == "link":
            target = raw.get(column.href or column.key)
            if target is not None and not isinstance(target, str):
                raise TableError(
                    f"{where}.{column.href or column.key}: a link target is a string"
                )
    return dict(raw)

