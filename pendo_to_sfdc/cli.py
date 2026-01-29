import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict

from pendo_to_sfdc.pendo_client import PendoClient
from pendo_to_sfdc.sfdc_client import SfdcClient
from pendo_to_sfdc.transform import (
    build_sfdc_records,
    ensure_external_id_present,
    normalize_results,
)


def _load_json(path: str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync a Pendo table into Salesforce.")
    parser.add_argument("--query-file", required=True, help="Path to the Pendo aggregation query JSON.")
    parser.add_argument("--mapping-file", required=True, help="Path to the Pendo-to-SFDC mapping JSON.")
    parser.add_argument(
        "--results-path",
        help="Optional dot path to the list of rows in the Pendo response.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of rows to send to SFDC.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and transform data but do not write to Salesforce.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def _validate_mapping(mapping: Dict[str, Any]) -> None:
    for required in ("sfdc_object", "external_id_field", "field_map"):
        if required not in mapping:
            raise ValueError(f"Mapping file is missing required key '{required}'.")
    if not isinstance(mapping["field_map"], dict) or not mapping["field_map"]:
        raise ValueError("Mapping file 'field_map' must be a non-empty object.")


def main() -> None:
    args = _build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    query_payload = _load_json(args.query_file)
    mapping = _load_json(args.mapping_file)
    _validate_mapping(mapping)

    results_path = args.results_path or mapping.get("results_path")
    columns_override = mapping.get("columns")

    pendo_client = PendoClient()
    logging.info("Querying Pendo aggregation API.")
    payload = pendo_client.run_query(query_payload)

    rows = normalize_results(payload, results_path=results_path, columns_override=columns_override)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    field_map = mapping["field_map"]
    static_fields = mapping.get("static_fields") or {}
    ignore_nulls = bool(mapping.get("ignore_nulls", False))
    records = build_sfdc_records(rows, field_map, static_fields, ignore_nulls)
    ensure_external_id_present(records, mapping["external_id_field"])

    logging.info("Prepared %d records for Salesforce.", len(records))

    if args.dry_run:
        preview = records[:5]
        logging.info("Dry run enabled. First %d records: %s", len(preview), json.dumps(preview))
        return

    sfdc_client = SfdcClient.from_env()
    logging.info("Upserting records into Salesforce %s.", mapping["sfdc_object"])
    results = sfdc_client.bulk_upsert(
        mapping["sfdc_object"],
        records,
        mapping["external_id_field"],
        batch_size=int(mapping.get("batch_size", 2000)),
        use_serial=bool(mapping.get("use_serial", True)),
    )
    logging.info("Salesforce bulk upsert completed with %d results.", len(results))


if __name__ == "__main__":
    main()
