import json

from app.analysis import build_prompt_v1


def _extract_stats_summary_json(prompt: str) -> dict:
    marker = "stats_summary_json:\n"
    assert marker in prompt
    tail = prompt.split(marker, 1)[1]
    json_part = tail.split("\n\n注意:", 1)[0].strip()
    return json.loads(json_part)


def testBuildPromptV1IncludesFormatAndStatsJson():
    stats = {
        "rows": 4,
        "columns": [
            {
                "name": "project",
                "kind": "string",
                "present_count": 4,
                "non_empty_count": 3,
                "numeric": None,
                "top_values": [{"value": "案件A", "count": 2}, {"value": "案件B", "count": 1}],
            },
            {
                "name": "amount",
                "kind": "number",
                "present_count": 4,
                "non_empty_count": 3,
                "numeric": {"count": 3, "min": 100.0, "max": 300.0, "avg": 200.0},
                "top_values": None,
            },
        ],
    }
    prompt = build_prompt_v1(stats, max_prompt_chars=9000)

    assert "## 注目点" in prompt
    assert "## 仮説（控えめ）" in prompt
    assert "## 追加で確認したいこと" in prompt
    assert "## 前提・限界" in prompt

    summary = _extract_stats_summary_json(prompt)
    assert summary["rows"] == 4
    assert summary["columns_count"] == 2
    assert summary["included_columns_count"] == 2


def testBuildPromptV1RespectsMaxPromptChars():
    # top_values を長くして prompt を膨らませ、サイズ上限で省略が入ることを確認する
    long_value = "x" * 300
    columns = []
    for i in range(50):
        columns.append(
            {
                "name": f"col_{i:03d}",
                "kind": "string",
                "present_count": 100,
                "non_empty_count": 100 - i,
                "numeric": None,
                "top_values": [
                    {"value": long_value, "count": 10},
                    {"value": long_value + "y", "count": 9},
                    {"value": long_value + "z", "count": 8},
                ],
            }
        )
    stats = {"rows": 100, "columns": columns}

    max_chars = 1600
    prompt = build_prompt_v1(
        stats,
        max_prompt_chars=max_chars,
        max_columns=30,
        max_top_values_per_column=3,
    )

    assert len(prompt) <= max_chars
    assert "注意: 入力サイズ上限" in prompt

    # 省略は入るが、JSON は壊れていないこと
    summary = _extract_stats_summary_json(prompt)
    assert summary["columns_count"] == 50
    assert summary["included_columns_count"] <= 30

