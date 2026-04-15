from __future__ import annotations

import json
from html import escape
from typing import cast


def render_html(payload: dict[str, object]) -> str:
    variant = _get_variant(payload)
    title = _get_page_title(payload, variant)
    algorithm_name = escape(str(payload["algorithm_name"]))
    model_family = escape(str(payload["model_family"]))
    label_mode = escape(str(payload["label_mode"]))
    reference_rule = escape(str(payload["reference_rule"]))
    generated_date = escape(str(payload["generated_date"]))
    latest_summary = cast(dict[str, object], payload.get("latest_summary", {}))
    latest_date = escape(str(latest_summary.get("latest_date", "")))
    lookback_days = escape(str(latest_summary.get("lookback_days", "")))
    default_chart_signal_mode = str(payload.get("default_chart_signal_mode", "raw"))
    initial_mode = "execution" if default_chart_signal_mode == "execution" else "raw"
    legend = cast(dict[str, object], payload.get("legend", {}))
    payload_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")

    return "".join(
        [
            "<!doctype html>",
            '<html lang="zh-Hant">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{title}</title>",
            "<style>",
            _render_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<div class="wrap">',
            '<div class="card">',
            f"<h1>{title}</h1>",
            _render_meta_header(
                algorithm_name=algorithm_name,
                model_family=model_family,
                label_mode=label_mode,
                reference_rule=reference_rule,
                generated_date=generated_date,
                signal_mode=escape(initial_mode) if variant == "signal" else None,
            ),
            _render_signal_body(
                generated_date=generated_date,
                latest_date=latest_date,
                lookback_days=lookback_days,
                initial_mode=initial_mode,
                legend=legend,
            )
            if variant == "signal"
            else _render_regression_body(payload=payload, legend=legend),
            "</div>",
            "</div>",
            '<div id="tooltip" class="tooltip"></div>',
            "<script>",
            f"const payload = {payload_json};",
            _render_chart_script(variant),
            "</script>",
            "</body></html>",
        ]
    )


def _get_variant(payload: dict[str, object]) -> str:
    payload_variant = payload.get("variant")
    if payload_variant in {"signal", "regression"}:
        explicit_variant = cast(str, payload_variant)
        inferred_variant = _infer_variant(payload)
        if explicit_variant != inferred_variant:
            raise ValueError(
                f"payload variant {explicit_variant!r} is incompatible with inferred {inferred_variant!r} payload shape"
            )
        return explicit_variant
    return _infer_variant(payload)


def _infer_variant(payload: dict[str, object]) -> str:
    return "regression" if isinstance(payload.get("recent_rows"), list) else "signal"


def _get_page_title(payload: dict[str, object], variant: str) -> str:
    if variant == "regression":
        return escape(str(payload.get("title") or payload["algorithm_label"]))
    return escape(str(payload["algorithm_label"]))


def _render_meta_header(
    *,
    algorithm_name: str,
    model_family: str,
    label_mode: str,
    reference_rule: str,
    generated_date: str,
    signal_mode: str | None,
) -> str:
    signal_mode_html = ""
    if signal_mode is not None:
        signal_mode_html = (
            f'<div class="meta-item"><span class="meta-label">Signal mode:</span>'
            f'<span class="meta-value">{signal_mode}</span></div>'
        )

    return (
        '<div class="meta-header">'
        f'<div class="meta-item"><span class="meta-label">Algorithm:</span><span class="meta-value">{algorithm_name}</span></div>'
        f'<div class="meta-item"><span class="meta-label">Model family:</span><span class="meta-value">{model_family}</span></div>'
        f'<div class="meta-item"><span class="meta-label">Label mode:</span><span class="meta-value">{label_mode}</span></div>'
        f'<div class="meta-item"><span class="meta-label">Reference rule:</span><span class="meta-value">{reference_rule}</span></div>'
        f"{signal_mode_html}"
        f'<div class="meta-item"><span class="meta-label">Generated from:</span><span class="meta-value">{generated_date}</span></div>'
        "</div>"
    )


def _render_signal_body(
    *,
    generated_date: str,
    latest_date: str,
    lookback_days: str,
    initial_mode: str,
    legend: dict[str, object],
) -> str:
    mode_execution_active = " active" if initial_mode == "execution" else ""
    mode_raw_active = " active" if initial_mode == "raw" else ""
    initial_mode_note = (
        "Current view: execution signal after buy-point overlay."
        if initial_mode == "execution"
        else "Current view: raw model signal before buy-point overlay."
    )

    return (
        f'<div class="sub">Generated date: {generated_date} · Latest date: {latest_date} · Lookback: {lookback_days}</div>'
        '<div class="mode-bar">'
        f'<button id="modeExecution" class="mode-button{mode_execution_active}" type="button">execution signal</button>'
        f'<button id="modeRaw" class="mode-button{mode_raw_active}" type="button">raw model signal</button>'
        f'<div id="modeNote" class="mode-note">{initial_mode_note}</div>'
        "</div>"
        f'<div class="legend">{_render_legend_items(legend)}</div>'
        '<div id="chart"></div>'
    )


def _render_regression_body(payload: dict[str, object], legend: dict[str, object]) -> str:
    latest_text = escape(str(payload.get("latest_text", "No rows")))
    selected_count = escape(str(payload.get("selected_count", 0)))
    recent_rows = cast(list[object], payload.get("recent_rows", []))
    recent_cards = "".join(_render_recent_card(cast(dict[str, object], row)) for row in recent_rows)

    return (
        f'<div class="sub">{latest_text}。目前視窗內 selected 共 <strong>{selected_count}</strong> 筆。</div>'
        '<div class="recent-panel">'
        '<div class="recent-summary">最近 5 筆會先用卡片看 selected 狀態、pred、percentile 與 cutoff；下方長條圖則用收盤價高度配合顏色看整段 watchlist 節奏。</div>'
        f'<div class="recent-grid">{recent_cards}</div>'
        "</div>"
        f'<div class="legend">{_render_legend_items(legend)}</div>'
        '<div id="chart"></div>'
    )


def _render_recent_card(row: dict[str, object]) -> str:
    render_state = _get_regression_render_state(row)
    signal_color = _get_regression_signal_color(render_state)

    return (
        '<div class="recent-card">'
        f'<div class="recent-date">{escape(str(row.get("date", "")))}</div>'
        f'<div class="recent-signal" style="color:{signal_color}">{escape(render_state)}</div>'
        f'<div class="recent-metric">pred={escape(_format_decimal(row.get("predicted_return"), 4))}</div>'
        f'<div class="recent-metric">pct={escape(_format_decimal(row.get("prediction_percentile"), 4))}</div>'
        f'<div class="recent-metric">cutoff={escape(_format_decimal(row.get("bucket_cutoff"), 4))}</div>'
        f'<div class="recent-metric">bucket={escape(str(row.get("bucket_direction", "")))} {escape(str(row.get("bucket_pct", "")))}%</div>'
        f'<div class="recent-metric">selected={"yes" if bool(row.get("selected")) else "no"}</div>'
        f'<div class="recent-metric">close={escape(_format_decimal(row.get("close"), 2))}</div>'
        "</div>"
    )


def _get_regression_render_state(row: dict[str, object]) -> str:
    render_state = row.get("render_state")
    if isinstance(render_state, str) and render_state:
        return render_state
    return "selected" if bool(row.get("selected")) else "idle"


def _get_regression_signal_color(render_state: str) -> str:
    if render_state == "selected":
        return "#065f46"
    if render_state == "watch":
        return "#f59e0b"
    return "#6b7280"


def _render_legend_items(legend: dict[str, object]) -> str:
    return "".join(
        (
            '<span class="legend-item">'
            f'<span class="swatch" style="background:{escape(str(color))}"></span>'
            f"{escape(str(name))}"
            "</span>"
        )
        for name, color in legend.items()
    )


def _format_decimal(value: object, digits: int) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return str(value or "")


def _render_styles() -> str:
    return (
        ":root { --bg: #f6f3ec; --ink: #1f2937; --muted: #6b7280; --grid: #d6d3d1; --panel: #fffdf8; }"
        "body { margin: 0; font-family: 'Segoe UI', 'Noto Sans TC', sans-serif; background: linear-gradient(180deg, #f6f3ec 0%, #ebe5da 100%); color: var(--ink); }"
        ".wrap { max-width: 1400px; margin: 0 auto; padding: 24px; }"
        ".card { background: var(--panel); border: 1px solid #e7e0d4; border-radius: 18px; box-shadow: 0 18px 60px rgba(31, 41, 55, 0.08); padding: 20px 20px 12px; }"
        "h1 { margin: 0 0 8px; font-size: 28px; }"
        ".meta-header { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px 16px; margin: 6px 0 14px; padding: 14px 16px; border: 1px solid #e7e0d4; border-radius: 14px; background: #faf7f1; }"
        ".meta-item { display: flex; flex-direction: column; gap: 4px; }"
        ".meta-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }"
        ".meta-value { font-size: 14px; font-weight: 600; word-break: break-word; }"
        ".sub { color: var(--muted); margin-bottom: 14px; }"
        ".legend { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 18px; font-size: 14px; }"
        ".legend-item { display: inline-flex; align-items: center; gap: 8px; }"
        ".swatch { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }"
        ".mode-bar { display: flex; gap: 10px; margin: 6px 0 14px; flex-wrap: wrap; align-items: center; }"
        ".mode-button { border: 1px solid #d9cfbe; background: #f8f3ea; color: var(--ink); border-radius: 999px; padding: 8px 14px; font-size: 13px; cursor: pointer; }"
        ".mode-button.active { background: #1f2937; color: #fffdf8; border-color: #1f2937; }"
        ".mode-note { color: var(--muted); font-size: 13px; }"
        ".recent-panel { display: grid; gap: 12px; margin-bottom: 18px; }"
        ".recent-summary { font-size: 14px; color: var(--muted); }"
        ".recent-grid { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 10px; }"
        ".recent-card { background: #faf6ee; border: 1px solid #eadfcb; border-radius: 12px; padding: 10px 12px; }"
        ".recent-date { font-size: 12px; color: var(--muted); margin-bottom: 4px; }"
        ".recent-signal { font-size: 16px; font-weight: 700; margin-bottom: 6px; }"
        ".recent-metric { font-size: 12px; color: var(--ink); line-height: 1.45; }"
        "#chart { width: 100%; overflow-x: auto; border-top: 1px solid #efe8db; padding-top: 10px; }"
        "svg { display: block; height: 560px; }"
        ".axis-label { fill: var(--muted); font-size: 11px; }"
        ".tooltip { position: fixed; pointer-events: none; background: rgba(17, 24, 39, 0.94); color: #fff; padding: 10px 12px; border-radius: 10px; font-size: 12px; line-height: 1.45; transform: translate(12px, 12px); display: none; white-space: pre-line; box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 360px; }"
    )


def _render_chart_script(variant: str) -> str:
    return "".join(
        [
            "const rows = payload.rows || [];",
            "const colors = payload.legend || {};",
            "const chart = document.getElementById('chart');",
            "const tooltip = document.getElementById('tooltip');",
            "const width = Math.max(2400, rows.length * 12);",
            "const height = 560;",
            "const topPad = 24;",
            "const priceHeight = 410;",
            "const axisTop = 450;",
            "const leftPad = 56;",
            "const rightPad = 24;",
            "const innerWidth = width - leftPad - rightPad;",
            "const barWidth = innerWidth / Math.max(rows.length, 1);",
            "const closes = rows.map((row) => row.close || 0);",
            "const minClose = rows.length ? Math.min(...closes) : 0;",
            "const maxClose = rows.length ? Math.max(...closes) : 1;",
            "const closeRange = Math.max(maxClose - minClose, 1);",
            "const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');",
            "svg.setAttribute('id', 'chartSvg');",
            "svg.setAttribute('viewBox', `0 0 ${width} ${height}`);",
            "svg.setAttribute('width', String(width));",
            "svg.setAttribute('height', String(height));",
            "const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');",
            "bg.setAttribute('x', '0');",
            "bg.setAttribute('y', '0');",
            "bg.setAttribute('width', String(width));",
            "bg.setAttribute('height', String(height));",
            "bg.setAttribute('fill', '#fffdf8');",
            "svg.appendChild(bg);",
            "for (let i = 0; i < 5; i += 1) {",
            "const y = topPad + (priceHeight / 4) * i;",
            "const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');",
            "line.setAttribute('x1', String(leftPad));",
            "line.setAttribute('x2', String(width - rightPad));",
            "line.setAttribute('y1', String(y));",
            "line.setAttribute('y2', String(y));",
            "line.setAttribute('stroke', '#d6d3d1');",
            "line.setAttribute('stroke-width', '1');",
            "line.setAttribute('stroke-dasharray', '3 5');",
            "svg.appendChild(line);",
            "const price = maxClose - (closeRange / 4) * i;",
            "const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');",
            "label.setAttribute('x', '8');",
            "label.setAttribute('y', String(y + 4));",
            "label.setAttribute('class', 'axis-label');",
            "label.textContent = price.toFixed(1);",
            "svg.appendChild(label);",
            "}",
            "const barsLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');",
            "svg.appendChild(barsLayer);",
            _render_signal_chart_script() if variant == "signal" else _render_regression_chart_script(),
            "const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');",
            "axisLine.setAttribute('x1', String(leftPad));",
            "axisLine.setAttribute('x2', String(width - rightPad));",
            "axisLine.setAttribute('y1', String(axisTop));",
            "axisLine.setAttribute('y2', String(axisTop));",
            "axisLine.setAttribute('stroke', '#6b7280');",
            "axisLine.setAttribute('stroke-width', '1');",
            "svg.appendChild(axisLine);",
            "const tickEvery = Math.max(1, Math.floor(rows.length / 20));",
            "rows.forEach((row, index) => {",
            "if (index % tickEvery !== 0 && index !== rows.length - 1) return;",
            "const x = leftPad + index * barWidth + barWidth / 2;",
            "const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');",
            "tick.setAttribute('x1', String(x));",
            "tick.setAttribute('x2', String(x));",
            "tick.setAttribute('y1', String(axisTop));",
            "tick.setAttribute('y2', String(axisTop + 8));",
            "tick.setAttribute('stroke', '#6b7280');",
            "svg.appendChild(tick);",
            "const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');",
            "label.setAttribute('x', String(x));",
            "label.setAttribute('y', String(axisTop + 24));",
            "label.setAttribute('text-anchor', 'middle');",
            "label.setAttribute('class', 'axis-label');",
            "label.textContent = row.date;",
            "svg.appendChild(label);",
            "});",
            "chart.appendChild(svg);",
            "requestAnimationFrame(() => { chart.scrollLeft = chart.scrollWidth; });",
        ]
    )


def _render_signal_chart_script() -> str:
    return (
        "const modeExecution = document.getElementById('modeExecution');"
        "const modeRaw = document.getElementById('modeRaw');"
        "const modeNote = document.getElementById('modeNote');"
        "let currentMode = payload.default_chart_signal_mode === 'execution' ? 'execution' : 'raw';"
        "function renderBars(mode) {"
        "barsLayer.replaceChildren();"
        "rows.forEach((row, index) => {"
        "const x = leftPad + index * barWidth;"
        "const normalized = ((row.close || 0) - minClose) / closeRange;"
        "const barHeight = Math.max(2, normalized * (priceHeight - 8));"
        "const y = topPad + priceHeight - barHeight;"
        "const displaySignal = mode === 'raw' ? row.raw_model_signal : row.signal;"
        "const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');"
        "rect.setAttribute('x', String(x));"
        "rect.setAttribute('y', String(y));"
        "rect.setAttribute('width', String(Math.max(1, barWidth - 1)));"
        "rect.setAttribute('height', String(barHeight));"
        "rect.setAttribute('fill', colors[displaySignal] || '#9ca3af');"
        "rect.setAttribute('rx', '1.5');"
        "rect.setAttribute('opacity', mode === 'raw' ? '0.96' : (row.buy_point_ok ? '1' : '0.42'));"
        "rect.setAttribute('stroke', mode === 'raw' ? 'none' : (row.buy_point_ok ? '#fffdf8' : 'none'));"
        "rect.setAttribute('stroke-width', mode === 'raw' ? '0' : (row.buy_point_ok ? '1.5' : '0'));"
        "rect.addEventListener('mousemove', (event) => {"
        "tooltip.style.display = 'block';"
        "tooltip.style.left = `${event.clientX}px`;"
        "tooltip.style.top = `${event.clientY}px`;"
        "tooltip.textContent = `${row.buy_point_ok ? 'buy_point pass' : 'buy_point blocked'}\n${row.date}\nclose=${row.close}\nsignal=${row.signal}\nmodel_signal=${row.raw_model_signal}\nchart_mode=${mode}\np=${row.probability}\ngap=${row.confidence_gap}\n${row.rule_name}=${row.rule_selected ? 'yes' : 'no'}\nbuy_point_note=${row.buy_point_warnings || 'clean'}\nmodel_reason=${row.model_rationale}\nrule_reason=${row.rule_rationale}\nret_20=${row.ret_20}\nret_60=${row.ret_60}\ndrawdown_20=${row.drawdown_20}\nsma_gap_20=${row.sma_gap_20}\nrsi_14=${row.rsi_14}`;"
        "});"
        "rect.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });"
        "barsLayer.appendChild(rect);"
        "});"
        "}"
        "function setMode(mode) {"
        "currentMode = mode;"
        "renderBars(mode);"
        "modeExecution.classList.toggle('active', mode === 'execution');"
        "modeRaw.classList.toggle('active', mode === 'raw');"
        "modeNote.textContent = mode === 'raw' ? 'Current view: raw model signal before buy-point overlay.' : 'Current view: execution signal after buy-point overlay.';"
        "}"
        "modeExecution.addEventListener('click', () => setMode('execution'));"
        "modeRaw.addEventListener('click', () => setMode('raw'));"
        "setMode(currentMode);"
    )


def _render_regression_chart_script() -> str:
    return (
        "function renderRegressionBars() {"
        "barsLayer.replaceChildren();"
        "rows.forEach((row, index) => {"
        "const x = leftPad + index * barWidth;"
        "const normalized = ((row.close || 0) - minClose) / closeRange;"
        "const barHeight = Math.max(2, normalized * (priceHeight - 8));"
        "const y = topPad + priceHeight - barHeight;"
        "const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');"
        "rect.setAttribute('x', String(x));"
        "rect.setAttribute('y', String(y));"
        "rect.setAttribute('width', String(Math.max(1, barWidth - 1)));"
        "rect.setAttribute('height', String(barHeight));"
        "const fillKey = row.render_state || 'idle';"
        "rect.setAttribute('fill', colors[fillKey] || '#f8d9a0');"
        "rect.setAttribute('rx', '1.5');"
        "rect.addEventListener('mousemove', (event) => {"
        "tooltip.style.display = 'block';"
        "tooltip.style.left = `${event.clientX}px`;"
        "tooltip.style.top = `${event.clientY}px`;"
        "tooltip.textContent = `${row.date}\nclose=${row.close}\npredicted_return=${row.predicted_return}\nfuture_return_60=${row.future_return_60}\npercentile=${row.prediction_percentile}\nbucket=${row.bucket_direction} ${row.bucket_pct}%\ncutoff=${row.bucket_cutoff}\nselected=${row.selected ? 'yes' : 'no'}`;"
        "});"
        "rect.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });"
        "barsLayer.appendChild(rect);"
        "});"
        "}"
        "renderRegressionBars();"
    )
