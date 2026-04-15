from __future__ import annotations

import json
from html import escape
from typing import cast


def render_html(payload: dict[str, object]) -> str:
    algorithm_label = escape(str(payload["algorithm_label"]))
    algorithm_name = escape(str(payload["algorithm_name"]))
    model_family = escape(str(payload["model_family"]))
    label_mode = escape(str(payload["label_mode"]))
    reference_rule = escape(str(payload["reference_rule"]))
    generated_date = escape(str(payload["generated_date"]))

    rows = []
    for row in cast(list[object], payload.get("rows", [])):
        row_data = row if isinstance(row, dict) else {}
        rows.append(
            "<tr "
            f"data-model_reason=\"{escape(str(row_data.get('model_rationale', '')))}\" "
            f"data-rule_reason=\"{escape(str(row_data.get('rule_rationale', '')))}\" "
            f"data-buy_point_note=\"{escape(str(row_data.get('buy_point_warnings', '')))}\">"
            f"<td>{escape(str(row_data.get('date', '')))}</td>"
            f"<td>{escape(str(row_data.get('signal', '')))}</td>"
            "</tr>"
        )

    payload_json = escape(json.dumps(payload, ensure_ascii=False))
    return (
        "<!doctype html>"
        "<html lang=\"en\">"
        "<head><meta charset=\"utf-8\"><title>"
        f"{algorithm_label}"
        "</title></head>"
        "<body>"
        f"<h1>{algorithm_label}</h1>"
        f"<div>Algorithm: {algorithm_name}</div>"
        f"<div>Model family: {model_family}</div>"
        f"<div>Label mode: {label_mode}</div>"
        f"<div>Reference rule: {reference_rule}</div>"
        f"<div>Generated date: {generated_date}</div>"
        "<table><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        f"<script type=\"application/json\" id=\"chart-payload\">{payload_json}</script>"
        "</body></html>"
    )
