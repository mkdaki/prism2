import json
from datetime import datetime, timezone

from .llm import LLMClient


def generate_template_analysis(stats: dict) -> dict:
    """LLMなしで stats から簡易要約を生成する（B-2-0互換）。"""
    rows = int(stats.get("rows") or 0)
    columns = stats.get("columns") or []

    kindCounts: dict[str, int] = {"number": 0, "string": 0, "mixed": 0, "empty": 0}
    for c in columns:
        kind = c.get("kind")
        if kind in kindCounts:
            kindCounts[kind] += 1

    numericCols = [c.get("name") for c in columns if c.get("kind") in ("number", "mixed")]
    stringCols = [c.get("name") for c in columns if c.get("kind") in ("string", "mixed")]

    lines: list[str] = []
    lines.append("これはPoCのため、B-1の統計（stats）から自動生成した簡易要約です（LLM未接続）。")
    lines.append(f"行数: {rows} / カラム数: {len(columns)}")
    lines.append(
        "カラム種別: "
        f"number={kindCounts['number']}, "
        f"string={kindCounts['string']}, "
        f"mixed={kindCounts['mixed']}, "
        f"empty={kindCounts['empty']}"
    )
    if numericCols:
        lines.append("数値として扱える列（mixed含む）: " + ", ".join([n for n in numericCols if n]))
    if stringCols:
        lines.append("文字列として扱える列（mixed含む）: " + ", ".join([n for n in stringCols if n]))

    generatedAt = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"generated_at": generatedAt, "analysis_text": "\n".join(lines)}


def _safe_int(v) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def _safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def compress_stats_for_prompt(
    stats: dict,
    *,
    max_columns: int = 30,
    max_top_values_per_column: int = 3,
) -> dict:
    """
    B-2-2: LLMへ送る入力を最小化する。
    - 行データは送らず、B-1 stats を必要な要素だけ抽出する
    - サイズ肥大化しやすい top_values / columns 数を制限する
    """
    rows = _safe_int(stats.get("rows"))
    columns = stats.get("columns") or []

    # 安定した順序（非空が多い列を優先、同率は名前で固定）
    def sort_key(c: dict):
        name = str(c.get("name") or "")
        non_empty = _safe_int(c.get("non_empty_count"))
        return (-non_empty, name)

    ordered = sorted([c for c in columns if isinstance(c, dict)], key=sort_key)
    limited = ordered[: max(0, int(max_columns))]

    out_cols: list[dict] = []
    for c in limited:
        item: dict = {
            "name": c.get("name"),
            "kind": c.get("kind"),
            "present_count": _safe_int(c.get("present_count")),
            "non_empty_count": _safe_int(c.get("non_empty_count")),
        }

        numeric = c.get("numeric")
        if isinstance(numeric, dict):
            item["numeric"] = {
                "count": _safe_int(numeric.get("count")),
                "min": _safe_float(numeric.get("min")),
                "max": _safe_float(numeric.get("max")),
                "avg": _safe_float(numeric.get("avg")),
            }
        else:
            item["numeric"] = None

        top_values = c.get("top_values")
        if isinstance(top_values, list):
            tv = []
            for t in top_values[: max(0, int(max_top_values_per_column))]:
                if not isinstance(t, dict):
                    continue
                tv.append({"value": t.get("value"), "count": _safe_int(t.get("count"))})
            item["top_values"] = tv
        else:
            item["top_values"] = None

        out_cols.append(item)

    return {
        "rows": rows,
        "columns_count": len(columns),
        "included_columns_count": len(out_cols),
        "columns": out_cols,
    }


def _render_prompt(instructions: str, summary: dict, *, truncated: bool) -> str:
    summary_json = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    note = ""
    if truncated:
        note = (
            "\n\n注意: 入力サイズ上限のため、statsの一部（列や頻出値など）を省略しています。\n"
            "省略により根拠が不足する場合は、断定せず「要確認」としてください。"
        )
    return f"{instructions}\n\nstats_summary_json:\n{summary_json}{note}\n"


def build_prompt_v1(
    stats: dict,
    *,
    max_columns: int = 30,
    max_top_values_per_column: int = 3,
    max_prompt_chars: int = 9000,
) -> str:
    """
    B-2-2: プロンプト v1（品質より再現性を優先）
    - 出力フォーマットを指示（見出し＋箇条書き）
    - stats入力を必要最小限に圧縮
    - 入力サイズ上限を超える場合は段階的に省略する
    """
    instructions = (
        "あなたはデータ分析アシスタントです。以下のデータセット統計（JSON）だけを根拠に、"
        "注目点と控えめな仮説を日本語で出力してください。\n"
        "\n"
        "制約:\n"
        "- 統計（stats）に根拠がないことは断定しない。推測する場合は推測と明記する。\n"
        "- 個人情報・機微情報の可能性がある値を、必要以上に繰り返さない。\n"
        "- 不確実な点は「追加で確認したいこと」に回す。\n"
        "\n"
        "出力フォーマット（必ずこの順で）:\n"
        "## 注目点\n"
        "- ...\n"
        "## 仮説（控えめ）\n"
        "- ...\n"
        "## 追加で確認したいこと\n"
        "- ...\n"
        "## 前提・限界\n"
        "- ...\n"
    )

    # Tier 0: まずは指定上限で圧縮
    summary0 = compress_stats_for_prompt(
        stats,
        max_columns=max_columns,
        max_top_values_per_column=max_top_values_per_column,
    )
    prompt0 = _render_prompt(instructions, summary0, truncated=False)
    if len(prompt0) <= max_prompt_chars:
        return prompt0

    # Tier 1: top_values を落とす（肥大化しやすい）
    summary1 = dict(summary0)
    cols1 = []
    for c in summary0.get("columns") or []:
        if not isinstance(c, dict):
            continue
        c2 = dict(c)
        c2["top_values"] = None
        cols1.append(c2)
    summary1["columns"] = cols1
    prompt1 = _render_prompt(instructions, summary1, truncated=True)
    if len(prompt1) <= max_prompt_chars:
        return prompt1

    # Tier 2: columns をさらに絞る
    summary2 = dict(summary1)
    cols2 = (summary1.get("columns") or [])[:10]
    summary2["columns"] = cols2
    summary2["included_columns_count"] = len(cols2)
    prompt2 = _render_prompt(instructions, summary2, truncated=True)
    if len(prompt2) <= max_prompt_chars:
        return prompt2

    # Tier 3: 最低限の概要（列名だけ）
    columns = stats.get("columns") or []
    names = []
    for c in columns:
        if isinstance(c, dict) and c.get("name"):
            names.append(str(c.get("name")))

    # 列名は長くなり得るので、まずは一定長で丸めておく（再現性とサイズ制御優先）
    names = [n[:64] for n in names]

    summary3 = {
        "rows": _safe_int(stats.get("rows")),
        "columns_count": len(columns),
        "included_columns_count": min(len(names), 50),
        "column_names": sorted(names)[:50],
    }

    # それでも上限を超える場合、列名の件数を段階的に減らして必ず収める（JSONは壊さない）
    while True:
        prompt3 = _render_prompt(instructions, summary3, truncated=True)
        if len(prompt3) <= max_prompt_chars:
            return prompt3
        cols = summary3.get("column_names") or []
        if len(cols) <= 1:
            # instructions が長すぎる場合など、ここまで縮めても入らないケース。
            # その場合は、列名を落として最小概要のみ返す。
            summary3["column_names"] = []
            summary3["included_columns_count"] = 0
            prompt_min = _render_prompt(instructions, summary3, truncated=True)
            if len(prompt_min) <= max_prompt_chars:
                return prompt_min
            # それでも収まらない場合は JSON 自体を省略し、指示文のみ返す（JSONを壊さない）
            fallback = (
                f"{instructions}\n\n"
                "注意: 入力サイズ上限のため、stats_summary_json は省略されました。\n"
                "統計に基づく推論は行わず、必要な追加情報を列挙してください。\n"
            )
            return fallback[:max_prompt_chars]
        summary3["column_names"] = cols[: max(1, len(cols) // 2)]
        summary3["included_columns_count"] = len(summary3["column_names"])


def generate_llm_analysis_text(stats: dict, llm: LLMClient) -> str:
    prompt = build_prompt_v1(stats)
    return llm.generate(prompt)


