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


def build_prompt_v0(stats: dict) -> str:
    """B-2-2で作り込む前の最小プロンプト（B-2-1の配線確認用）。"""
    statsJson = json.dumps(stats, ensure_ascii=False, sort_keys=True)
    return (
        "以下のデータセット統計（JSON）を読み、注目点と仮説を箇条書きで短く出力してください。\n"
        "過度な断定は避け、根拠がstatsに無いことは推測しないでください。\n\n"
        f"stats:\n{statsJson}\n"
    )


def generate_llm_analysis_text(stats: dict, llm: LLMClient) -> str:
    prompt = build_prompt_v0(stats)
    return llm.generate(prompt)


