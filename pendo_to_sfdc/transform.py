import json
from typing import Any, Dict, Iterable, List, Mapping, Optional


def _split_path(path: str) -> List[str]:
    return [part for part in path.split(".") if part]


def get_by_path(data: Any, path: str) -> Any:
    current = data
    for raw_part in _split_path(path):
        if isinstance(current, Mapping):
            current = current.get(raw_part)
        elif isinstance(current, list):
            try:
                index = int(raw_part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
        else:
            return None
        if current is None:
            return None
    return current


def normalize_results(
    payload: Any,
    results_path: Optional[str] = None,
    columns_override: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if results_path:
        extracted = get_by_path(payload, results_path)
        if not isinstance(extracted, list):
            raise ValueError(f"results_path '{results_path}' did not resolve to a list.")
        return _rows_from_extracted(extracted, columns_override)

    if isinstance(payload, list):
        return _rows_from_extracted(payload, columns_override)

    if isinstance(payload, Mapping):
        if "results" in payload:
            return _rows_from_extracted(payload.get("results"), columns_override, payload)
        if "rows" in payload:
            return _rows_from_extracted(payload.get("rows"), columns_override, payload)

    raise ValueError(
        "Unable to locate Pendo results in response. Provide results_path in the mapping "
        "file or use --results-path to point at the list of rows."
    )


def _rows_from_extracted(
    extracted: Any,
    columns_override: Optional[List[str]],
    payload: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if not isinstance(extracted, list):
        raise ValueError("Pendo results payload is not a list.")
    if not extracted:
        return []

    if isinstance(extracted[0], Mapping):
        return [dict(row) for row in extracted]

    if not isinstance(extracted[0], list):
        raise ValueError("Pendo results list is not a list of objects or rows.")

    columns = columns_override or _columns_from_payload(payload)
    if not columns:
        raise ValueError(
            "Pendo results returned arrays but no column metadata was found. "
            "Provide 'columns' in the mapping file to align values."
        )

    normalized = []
    for row in extracted:
        row_map = {}
        for idx, value in enumerate(row):
            key = columns[idx] if idx < len(columns) else f"column_{idx}"
            row_map[key] = value
        normalized.append(row_map)
    return normalized


def _columns_from_payload(payload: Optional[Mapping[str, Any]]) -> List[str]:
    if not payload:
        return []
    metadata = payload.get("metadata") or {}
    columns = metadata.get("columns") or metadata.get("fields") or payload.get("columns")
    if not isinstance(columns, list):
        return []

    normalized = []
    for idx, column in enumerate(columns):
        if isinstance(column, str):
            normalized.append(column)
            continue
        if isinstance(column, Mapping):
            for key in ("name", "field", "id", "label", "title", "displayName"):
                value = column.get(key)
                if value:
                    normalized.append(str(value))
                    break
            else:
                normalized.append(f"column_{idx}")
        else:
            normalized.append(f"column_{idx}")
    return normalized


def normalize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def build_sfdc_records(
    rows: Iterable[Mapping[str, Any]],
    field_map: Mapping[str, str],
    static_fields: Mapping[str, Any] | None = None,
    ignore_nulls: bool = False,
) -> List[Dict[str, Any]]:
    static_fields = static_fields or {}
    records = []
    for row in rows:
        record: Dict[str, Any] = {}
        for pendo_path, sfdc_field in field_map.items():
            value = get_by_path(row, pendo_path)
            if value is None and ignore_nulls:
                continue
            record[sfdc_field] = normalize_value(value)
        for sfdc_field, value in static_fields.items():
            if value is None and ignore_nulls:
                continue
            record[sfdc_field] = normalize_value(value)
        records.append(record)
    return records


def ensure_external_id_present(
    records: Iterable[Mapping[str, Any]], external_id_field: str
) -> None:
    for idx, record in enumerate(records):
        if external_id_field not in record or record.get(external_id_field) in ("", None):
            raise ValueError(
                f"Record {idx} is missing the external ID field '{external_id_field}'. "
                "Check your field_map or static_fields."
            )
