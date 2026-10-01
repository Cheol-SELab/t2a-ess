#!/usr/bin/env python3
"""CLI: T2A-ESS slot JSON -> SysML v2 textual model.

    python src/convert_t2a_to_sysml.py <t2a-ess.json> [-o out.sysml]

Reads a Text2Activity Extraction Slot (T2A-ESS) JSON and writes a SysML v2 file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from t2a_sysml import (  # noqa: E402
    convert_file,
    convert_state_model,
    load_model,
    state_summary,
    summarize,
    validate_effbd,
    validate_schema,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="T2A-ESS JSON file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="output .sysml (default: <input>.sysml)")
    parser.add_argument(
        "--imm-tags",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="IMM metadata tags (#Performer/#Function) + IMMBaseSchema import (default on; the EFFBD editor's canonical form). --no-imm-tags emits the plain (business_example) form.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Schema (Slot Relation contract) + EFFBD structure validation report; exit 4 if there is an error.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Same as --validate but writes no .sysml.",
    )
    parser.add_argument(
        "--state",
        action="store_true",
        help="Also generate the State View (standard SysML v2 state def).",
    )
    parser.add_argument(
        "--state-output",
        type=Path,
        default=None,
        help="State view output path (default: <output>.sysml -> .state.sysml); implies --state.",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 2

    model = load_model(args.input)
    sysml = convert_file(args.input, imm_tags=args.imm_tags)
    if args.validate_only:
        output = None
    else:
        output = args.output or args.input.with_suffix(".sysml")
        output.write_text(sysml, encoding="utf-8", newline="\n")  # LF on every platform

    want_state = args.state or args.state_output is not None
    state_sysml = convert_state_model(model) if want_state else None
    state_output = None
    if want_state and not args.validate_only:
        if args.state_output:
            state_output = args.state_output
        else:
            base = args.output or args.input.with_suffix(".sysml")
            state_output = Path(str(base)[: -len(".sysml")] + ".state.sysml") if str(base).endswith(".sysml") else Path(str(base) + ".state.sysml")
        state_output.write_text(state_sysml, encoding="utf-8", newline="\n")

    print(
        f"OK  {args.input.name} -> {output.name if output else '(not written)'}\n"
        f"  performers={len(model.collection('performers'))} "
        f"actions={len(model.collection('actions'))} "
        f"items={len(model.collection('items'))} "
        f"flows={len(model.collection('flows'))} "
        f"relations={len(model.relations)}\n"
        f"  sysml lines={sysml.count(chr(10))}"
    )
    if want_state:
        s = state_summary(model)
        print(
            f"  state: regions={s['regions']} states={s['states']} "
            f"transitions={s['transitions']} -> {state_output.name if state_output else '(not written)'}"
        )
    if args.validate or args.validate_only:
        schema_issues = validate_schema(model)
        effbd_issues = validate_effbd(model)
        schema_s, effbd_s = summarize(schema_issues), summarize(effbd_issues)
        print(f"  validate: schema errors={schema_s['errors']} warnings={schema_s['warnings']} | "
              f"effbd ok={effbd_s['ok']} errors={effbd_s['errors']} warnings={effbd_s['warnings']}")
        for issue in schema_issues:
            print(f"    schema: [{issue.severity}] {issue.code}: {issue.message}")
        for issue in effbd_issues:
            print(f"    effbd: [{issue.severity}] {issue.code}: {issue.message}")
        if schema_s["errors"] or not effbd_s["ok"]:
            return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
