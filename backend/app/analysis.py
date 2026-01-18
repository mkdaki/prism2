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

    # Tier 3 でも max_columns を尊重する（表示する列名の上限）
    max_names = min(50, max(0, int(max_columns)))

    summary3 = {
        "rows": _safe_int(stats.get("rows")),
        "columns_count": len(columns),
        "included_columns_count": min(len(names), max_names),
        "column_names": sorted(names)[:max_names],
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


def build_comparison_prompt_v1(comparison_data: dict) -> str:
    """
    目的: 2つのデータセットの比較結果からLLM用プロンプトを生成する（E-0-3）
    
    Args:
        comparison_data: compareDatasets() の返り値
            - base_dataset: {dataset_id, filename, created_at, rows}
            - target_dataset: {dataset_id, filename, created_at, rows}
            - comparison: {rows_change, columns_change}
    
    Returns:
        LLMに送信するプロンプト文字列
    """
    base = comparison_data.get("base_dataset") or {}
    target = comparison_data.get("target_dataset") or {}
    comparison = comparison_data.get("comparison") or {}
    
    rows_change = comparison.get("rows_change") or {}
    columns_change = comparison.get("columns_change") or []
    
    # メタ情報の抽出
    base_filename = base.get("filename", "不明")
    base_created_at = str(base.get("created_at", "不明"))
    base_rows = rows_change.get("base", 0)
    
    target_filename = target.get("filename", "不明")
    target_created_at = str(target.get("created_at", "不明"))
    target_rows = rows_change.get("target", 0)
    
    rows_diff = rows_change.get("diff", 0)
    rows_percent = rows_change.get("percent", 0.0)
    
    # 統計差分の整形
    diff_lines = []
    diff_lines.append(f"- 行数: {base_rows} → {target_rows} ({rows_diff:+d}件, {rows_percent:+.1f}%)")
    
    # 数値カラムの変化を抽出
    for col in columns_change:
        if not isinstance(col, dict):
            continue
        
        col_name = col.get("name", "不明")
        col_kind = col.get("kind", "")
        base_stats = col.get("base")
        target_stats = col.get("target")
        diff_stats = col.get("diff")
        
        # 数値カラムで両方に統計があり、差分がある場合のみ出力
        if (col_kind in ("number", "mixed") and 
            isinstance(base_stats, dict) and 
            isinstance(target_stats, dict) and 
            isinstance(diff_stats, dict)):
            
            # 平均値の変化
            base_avg = base_stats.get("avg")
            target_avg = target_stats.get("avg")
            diff_avg = diff_stats.get("avg")
            if base_avg is not None and target_avg is not None and diff_avg is not None:
                percent_change = (diff_avg / base_avg * 100.0) if base_avg != 0 else 0.0
                diff_lines.append(
                    f"- {col_name}（数値）: 平均 {base_avg:.1f} → {target_avg:.1f} "
                    f"({diff_avg:+.1f}, {percent_change:+.1f}%)"
                )
            
            # 最小値の変化
            base_min = base_stats.get("min")
            target_min = target_stats.get("min")
            diff_min = diff_stats.get("min")
            if base_min is not None and target_min is not None and diff_min is not None and diff_min != 0:
                diff_lines.append(
                    f"- {col_name}（数値）: 最小値 {base_min:.1f} → {target_min:.1f} ({diff_min:+.1f})"
                )
            
            # 最大値の変化
            base_max = base_stats.get("max")
            target_max = target_stats.get("max")
            diff_max = diff_stats.get("max")
            if base_max is not None and target_max is not None and diff_max is not None and diff_max != 0:
                diff_lines.append(
                    f"- {col_name}（数値）: 最大値 {base_max:.1f} → {target_max:.1f} ({diff_max:+.1f})"
                )
    
    diff_summary = "\n".join(diff_lines) if diff_lines else "- 有意な変化はありません"
    
    # プロンプトの構築
    instructions = (
        "あなたはデータアナリストです。以下の2つのデータセットの統計差分を分析し、\n"
        "変化の要点を簡潔に報告してください。\n"
        "\n"
        f"【基準データ】\n"
        f"ファイル名: {base_filename}\n"
        f"作成日時: {base_created_at}\n"
        f"行数: {base_rows}\n"
        "\n"
        f"【比較対象データ】\n"
        f"ファイル名: {target_filename}\n"
        f"作成日時: {target_created_at}\n"
        f"行数: {target_rows}\n"
        "\n"
        f"【統計差分】\n"
        f"{diff_summary}\n"
        "\n"
        "制約:\n"
        "- 統計差分に根拠がないことは断定しない。推測する場合は推測と明記する。\n"
        "- 過度な断定を避け、控えめな表現を使う。\n"
        "- 数値の変化率を具体的に指摘する。\n"
        "- 個人情報・機微情報の可能性がある値を、必要以上に繰り返さない。\n"
        "\n"
        "出力フォーマット（必ずこの順で）:\n"
        "## 変化の概要\n"
        "- ...\n"
        "## 注目すべき変化\n"
        "- ...\n"
        "## トレンド分析\n"
        "- ...\n"
        "## 前提・限界\n"
        "- ...\n"
    )
    
    return instructions


def build_comparison_prompt_v2(comparison_data: dict) -> str:
    """
    目的: ビジネス文脈重視の比較分析プロンプトを生成（E-2-2-1-3）
    
    Args:
        comparison_data: compareDatasets() の返り値
            - base_dataset: {dataset_id, filename, created_at, rows}
            - target_dataset: {dataset_id, filename, created_at, rows}
            - comparison: {rows_change, columns_change}
            - price_range_analysis: {base, target, changes}
            - keyword_analysis: {increased_keywords, decreased_keywords, new_keywords, disappeared_keywords}
    
    Returns:
        LLMに送信するプロンプト文字列（ビジネス指標優先）
    
    Notes:
        - 技術的指標（No, Page, rowOrder）を最小化
        - ビジネス指標（価格帯、キーワード）を最優先
        - アクション指向の分析を促す
    """
    base = comparison_data.get("base_dataset") or {}
    target = comparison_data.get("target_dataset") or {}
    comparison = comparison_data.get("comparison") or {}
    price_range_analysis = comparison_data.get("price_range_analysis") or {}
    keyword_analysis = comparison_data.get("keyword_analysis") or {}
    
    rows_change = comparison.get("rows_change") or {}
    
    # メタ情報の抽出
    base_filename = base.get("filename", "不明")
    base_created_at = str(base.get("created_at", "不明"))
    base_rows = rows_change.get("base", 0)
    
    target_filename = target.get("filename", "不明")
    target_created_at = str(target.get("created_at", "不明"))
    target_rows = rows_change.get("target", 0)
    
    rows_diff = rows_change.get("diff", 0)
    rows_percent = rows_change.get("percent", 0.0)
    
    # 1. 価格帯分析の整形
    price_section = ""
    if price_range_analysis:
        base_price = price_range_analysis.get("base") or {}
        target_price = price_range_analysis.get("target") or {}
        changes = price_range_analysis.get("changes") or {}
        
        price_lines = []
        price_lines.append("【価格帯別の案件数】")
        
        # 高単価案件（80万円以上）
        high_base = base_price.get("high", 0)
        high_target = target_price.get("high", 0)
        high_change = changes.get("high") or {}
        high_diff = high_change.get("diff", 0)
        high_percent = high_change.get("percent", 0.0)
        price_lines.append(
            f"- 高単価案件（80万円以上）: {high_base}件 → {high_target}件 "
            f"({high_diff:+d}件, {high_percent:+.1f}%)"
        )
        
        # 中単価案件（50-80万円）
        mid_base = base_price.get("mid", 0)
        mid_target = target_price.get("mid", 0)
        mid_change = changes.get("mid") or {}
        mid_diff = mid_change.get("diff", 0)
        mid_percent = mid_change.get("percent", 0.0)
        price_lines.append(
            f"- 中単価案件（50-80万円）: {mid_base}件 → {mid_target}件 "
            f"({mid_diff:+d}件, {mid_percent:+.1f}%)"
        )
        
        # 低単価案件（50万円未満）
        low_base = base_price.get("low", 0)
        low_target = target_price.get("low", 0)
        low_change = changes.get("low") or {}
        low_diff = low_change.get("diff", 0)
        low_percent = low_change.get("percent", 0.0)
        price_lines.append(
            f"- 低単価案件（50万円未満）: {low_base}件 → {low_target}件 "
            f"({low_diff:+d}件, {low_percent:+.1f}%)"
        )
        
        # 不明案件
        unknown_base = base_price.get("unknown", 0)
        unknown_target = target_price.get("unknown", 0)
        unknown_change = changes.get("unknown") or {}
        unknown_diff = unknown_change.get("diff", 0)
        unknown_percent = unknown_change.get("percent", 0.0)
        price_lines.append(
            f"- 価格不明案件: {unknown_base}件 → {unknown_target}件 "
            f"({unknown_diff:+d}件, {unknown_percent:+.1f}%)"
        )
        
        price_section = "\n".join(price_lines)
    else:
        price_section = "価格帯分析データがありません。"
    
    # 2. キーワード分析の整形
    keyword_section = ""
    if keyword_analysis:
        keyword_lines = []
        keyword_lines.append("【案件内容のキーワード変化】")
        
        # 増加キーワード（Top5）
        increased = keyword_analysis.get("increased_keywords") or []
        if increased:
            keyword_lines.append("\n増加キーワード（Top5）:")
            for kw in increased[:5]:
                keyword_lines.append(
                    f"  - {kw['keyword']}: {kw['base']}件 → {kw['target']}件 ({kw['diff']:+d}件)"
                )
        
        # 減少キーワード（Top5）
        decreased = keyword_analysis.get("decreased_keywords") or []
        if decreased:
            keyword_lines.append("\n減少キーワード（Top5）:")
            for kw in decreased[:5]:
                keyword_lines.append(
                    f"  - {kw['keyword']}: {kw['base']}件 → {kw['target']}件 ({kw['diff']:+d}件)"
                )
        
        # 新規出現キーワード
        new_keywords = keyword_analysis.get("new_keywords") or []
        if new_keywords:
            keyword_lines.append(f"\n新規出現キーワード: {', '.join(new_keywords[:10])}")
        
        # 消失キーワード
        disappeared = keyword_analysis.get("disappeared_keywords") or []
        if disappeared:
            keyword_lines.append(f"\n消失キーワード: {', '.join(disappeared[:10])}")
        
        keyword_section = "\n".join(keyword_lines)
    else:
        keyword_section = "キーワード分析データがありません。"
    
    # 3. プロンプトの構築
    instructions = (
        "あなたはフリーランスエンジニア市場のビジネスアナリストです。\n"
        "以下の2つのデータセットの比較結果を分析し、**ビジネス的に価値のある示唆**を提供してください。\n"
        "\n"
        f"【基準データ】\n"
        f"ファイル名: {base_filename}\n"
        f"作成日時: {base_created_at}\n"
        f"案件数: {base_rows}件\n"
        "\n"
        f"【比較対象データ】\n"
        f"ファイル名: {target_filename}\n"
        f"作成日時: {target_created_at}\n"
        f"案件数: {target_rows}件\n"
        f"案件数の変化: {rows_diff:+d}件 ({rows_percent:+.1f}%)\n"
        "\n"
        f"{price_section}\n"
        "\n"
        f"{keyword_section}\n"
        "\n"
        "分析の指針:\n"
        "- **ビジネス視点**: 価格帯の変化、技術トレンドの変化から市場動向を読み取る\n"
        "- **アクション指向**: フリーランスエンジニアが「次に何をすべきか」を提案する\n"
        "- **根拠の明確化**: データに基づく分析と推測を区別する\n"
        "- **技術トレンド**: 増加/減少キーワードから技術の需要変化を分析する\n"
        "\n"
        "出力フォーマット（必ずこの順で、各セクションを含める）:\n"
        "\n"
        "## ビジネス動向サマリー\n"
        "[1-2文で全体像を述べる。価格帯とキーワードの変化から見える市場のトレンド]\n"
        "\n"
        "## 価格動向\n"
        "[高/中/低単価案件の変化を分析。ビジネス的な示唆を述べる]\n"
        "- 高単価案件の増減とその意味\n"
        "- 中単価案件の増減とその意味\n"
        "- 低単価案件の増減とその意味\n"
        "- 価格動向から読み取れる市場の変化\n"
        "\n"
        "## 案件内容のトレンド\n"
        "[キーワードの増減から技術トレンドを分析]\n"
        "- 増加している技術・分野とその背景\n"
        "- 減少している技術・分野とその背景\n"
        "- 新規出現したキーワードの意味\n"
        "- 技術トレンドの今後の予測\n"
        "\n"
        "## 推奨アクション\n"
        "[フリーランスエンジニアが取るべき具体的なアクション3-5つ]\n"
        "- スキル強化の優先順位\n"
        "- 注目すべき技術領域\n"
        "- 避けるべきリスク\n"
        "\n"
        "## 前提・限界\n"
        "[この分析の前提条件、注意点、限界を明記]\n"
        "- データの期間や件数に関する注意点\n"
        "- 推測と事実の区別\n"
        "- より詳細な分析に必要な情報\n"
    )
    
    return instructions


def generate_comparison_template_analysis(comparison_data: dict) -> dict:
    """
    目的: LLMなしで比較結果から簡易要約を生成する（E-0-3、テスト用）
    
    Args:
        comparison_data: compareDatasets() の返り値
    
    Returns:
        {generated_at, analysis_text}
    """
    base = comparison_data.get("base_dataset") or {}
    target = comparison_data.get("target_dataset") or {}
    comparison = comparison_data.get("comparison") or {}
    
    rows_change = comparison.get("rows_change") or {}
    columns_change = comparison.get("columns_change") or []
    
    base_filename = base.get("filename", "不明")
    target_filename = target.get("filename", "不明")
    
    base_rows = rows_change.get("base", 0)
    target_rows = rows_change.get("target", 0)
    rows_diff = rows_change.get("diff", 0)
    rows_percent = rows_change.get("percent", 0.0)
    
    # 数値カラムの変化をカウント
    numeric_changes = []
    for col in columns_change:
        if not isinstance(col, dict):
            continue
        
        col_name = col.get("name", "不明")
        diff_stats = col.get("diff")
        
        if isinstance(diff_stats, dict):
            diff_avg = diff_stats.get("avg")
            if diff_avg is not None and diff_avg != 0:
                numeric_changes.append(col_name)
    
    lines = []
    lines.append("これはPoCのため、比較結果から自動生成した簡易要約です（LLM未接続）。")
    lines.append("")
    lines.append("## 変化の概要")
    lines.append(f"- 基準データ: {base_filename} ({base_rows}行)")
    lines.append(f"- 比較対象データ: {target_filename} ({target_rows}行)")
    lines.append(f"- 行数の変化: {rows_diff:+d}件 ({rows_percent:+.1f}%)")
    lines.append("")
    lines.append("## 注目すべき変化")
    if numeric_changes:
        lines.append(f"- 数値カラムの変化: {', '.join(numeric_changes[:5])}")
    else:
        lines.append("- 有意な数値変化は検出されませんでした")
    lines.append("")
    lines.append("## トレンド分析")
    if rows_diff > 0:
        lines.append("- データ件数が増加傾向にあります")
    elif rows_diff < 0:
        lines.append("- データ件数が減少傾向にあります")
    else:
        lines.append("- データ件数に変化はありません")
    lines.append("")
    lines.append("## 前提・限界")
    lines.append("- この要約はテンプレートベースで生成されており、深い洞察は含まれません")
    lines.append("- 詳細な分析には LLM を有効化してください")
    
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"generated_at": generated_at, "analysis_text": "\n".join(lines)}


def generate_comparison_analysis_text(
    comparison_data: dict, 
    llm: LLMClient,
    version: str = "v1"
) -> str:
    """
    目的: 比較結果からLLMによる推移分析テキストを生成する（E-0-3, E-2-2-1-3）
    
    Args:
        comparison_data: compareDatasets() の返り値
        llm: LLMクライアント
        version: プロンプトバージョン ("v1" or "v2")
    
    Returns:
        LLM生成の分析テキスト
    """
    if version == "v2":
        prompt = build_comparison_prompt_v2(comparison_data)
    else:
        prompt = build_comparison_prompt_v1(comparison_data)
    
    return llm.generate(prompt)


def calculate_stats_diff(base_stats: dict, target_stats: dict) -> dict:
    """
    目的: 2つのデータセット統計情報の差分を計算する（E-0-2）。
    
    Args:
        base_stats: 基準データの統計情報（getDatasetStats の結果）
        target_stats: 比較対象データの統計情報（getDatasetStats の結果）
    
    Returns:
        差分情報を含む辞書
    """
    base_rows = _safe_int(base_stats.get("rows"))
    target_rows = _safe_int(target_stats.get("rows"))
    
    # 行数の変化
    rows_diff = target_rows - base_rows
    rows_percent = (rows_diff / base_rows * 100.0) if base_rows > 0 else 0.0
    
    rows_change = {
        "base": base_rows,
        "target": target_rows,
        "diff": rows_diff,
        "percent": round(rows_percent, 2)
    }
    
    # カラムごとの変化を計算
    base_columns = {c["name"]: c for c in base_stats.get("columns", []) if isinstance(c, dict)}
    target_columns = {c["name"]: c for c in target_stats.get("columns", []) if isinstance(c, dict)}
    
    # すべてのカラム名を取得（base と target の和集合）
    all_column_names = sorted(set(base_columns.keys()) | set(target_columns.keys()))
    
    columns_change = []
    for col_name in all_column_names:
        base_col = base_columns.get(col_name)
        target_col = target_columns.get(col_name)
        
        item = {
            "name": col_name,
            "kind": None,
            "base": None,
            "target": None,
            "diff": None
        }
        
        # kind の決定（target を優先、なければ base）
        if target_col:
            item["kind"] = target_col.get("kind")
        elif base_col:
            item["kind"] = base_col.get("kind")
        
        # 数値カラムの差分計算
        if base_col and target_col:
            base_numeric = base_col.get("numeric")
            target_numeric = target_col.get("numeric")
            
            if isinstance(base_numeric, dict) and isinstance(target_numeric, dict):
                base_min = _safe_float(base_numeric.get("min"))
                base_max = _safe_float(base_numeric.get("max"))
                base_avg = _safe_float(base_numeric.get("avg"))
                
                target_min = _safe_float(target_numeric.get("min"))
                target_max = _safe_float(target_numeric.get("max"))
                target_avg = _safe_float(target_numeric.get("avg"))
                
                item["base"] = {
                    "min": base_min,
                    "max": base_max,
                    "avg": base_avg
                }
                item["target"] = {
                    "min": target_min,
                    "max": target_max,
                    "avg": target_avg
                }
                
                # 差分計算（None がある場合は None）
                diff_min = None
                diff_max = None
                diff_avg = None
                
                if base_min is not None and target_min is not None:
                    diff_min = round(target_min - base_min, 2)
                if base_max is not None and target_max is not None:
                    diff_max = round(target_max - base_max, 2)
                if base_avg is not None and target_avg is not None:
                    diff_avg = round(target_avg - base_avg, 2)
                
                item["diff"] = {
                    "min": diff_min,
                    "max": diff_max,
                    "avg": diff_avg
                }
            else:
                # どちらかに数値統計がない場合
                if isinstance(base_numeric, dict):
                    item["base"] = {
                        "min": _safe_float(base_numeric.get("min")),
                        "max": _safe_float(base_numeric.get("max")),
                        "avg": _safe_float(base_numeric.get("avg"))
                    }
                if isinstance(target_numeric, dict):
                    item["target"] = {
                        "min": _safe_float(target_numeric.get("min")),
                        "max": _safe_float(target_numeric.get("max")),
                        "avg": _safe_float(target_numeric.get("avg"))
                    }
        elif base_col:
            # target にカラムが存在しない場合
            base_numeric = base_col.get("numeric")
            if isinstance(base_numeric, dict):
                item["base"] = {
                    "min": _safe_float(base_numeric.get("min")),
                    "max": _safe_float(base_numeric.get("max")),
                    "avg": _safe_float(base_numeric.get("avg"))
                }
        elif target_col:
            # base にカラムが存在しない場合
            target_numeric = target_col.get("numeric")
            if isinstance(target_numeric, dict):
                item["target"] = {
                    "min": _safe_float(target_numeric.get("min")),
                    "max": _safe_float(target_numeric.get("max")),
                    "avg": _safe_float(target_numeric.get("avg"))
                }
        
        columns_change.append(item)
    
    return {
        "rows_change": rows_change,
        "columns_change": columns_change
    }


def extract_price_value(price_str: str | None) -> float | None:
    """
    目的: UnitPrice文字列から数値を抽出する（E-2-2改善タスク1）
    
    Args:
        price_str: 価格文字列（例: "80万円/月", "50-60万円", "¥800,000", None, "応相談"）
    
    Returns:
        抽出した価格（万円単位）。解析不可の場合は None。
        範囲指定の場合は中央値を返す（例: "50-60万円" → 55.0）
    
    Examples:
        "80万円/月" → 80.0
        "50-60万円" → 55.0
        "¥800,000" → 80.0
        None → None
        "" → None
        "応相談" → None
    """
    import re
    
    # 1. None/空文字チェック
    if price_str is None or price_str == "":
        return None
    
    price_str = str(price_str).strip()
    if not price_str:
        return None
    
    # 2. "万円"パターンのマッチング（例: "80万円/月", "50-60万円"）
    # パターン: 数値-数値万円 または 数値万円
    pattern_man_yen = r'(\d+(?:\.\d+)?)\s*[-~〜]\s*(\d+(?:\.\d+)?)\s*万円|(\d+(?:\.\d+)?)\s*万円'
    match = re.search(pattern_man_yen, price_str)
    
    if match:
        if match.group(1) and match.group(2):
            # 範囲指定（例: "50-60万円"）→ 中央値
            start = float(match.group(1))
            end = float(match.group(2))
            return round((start + end) / 2, 1)
        elif match.group(3):
            # 単一値（例: "80万円"）
            return float(match.group(3))
    
    # 3. カンマ区切り数値のパターン（例: "¥800,000", "800,000円"）
    # カンマを削除して数値を抽出
    pattern_comma = r'[\¥$]?\s*(\d{1,3}(?:,\d{3})+)(?:円)?'
    match_comma = re.search(pattern_comma, price_str)
    
    if match_comma:
        # カンマを削除して数値化
        num_str = match_comma.group(1).replace(',', '')
        try:
            value = float(num_str)
            # 1万円以上の場合は万円単位に変換
            if value >= 10000:
                return round(value / 10000, 1)
            else:
                # 1万円未満の場合はそのまま（万円単位として扱う）
                return round(value, 1)
        except ValueError:
            pass
    
    # 4. 純粋な数値パターン（例: "80", "800000"）
    pattern_number = r'(\d+(?:\.\d+)?)'
    match_number = re.search(pattern_number, price_str)
    
    if match_number:
        try:
            value = float(match_number.group(1))
            # 1000以上の場合は万円単位に変換（例: 800000 → 80）
            if value >= 1000:
                return round(value / 10000, 1)
            else:
                # 1000未満の場合はそのまま万円単位として扱う
                return round(value, 1)
        except ValueError:
            pass
    
    # 5. すべてのパターンにマッチしない場合は None
    return None


def classify_price_range(price: float | None) -> str:
    """
    目的: 価格を価格帯に分類する（E-2-2改善タスク1）
    
    Args:
        price: 価格（万円単位）。None の場合は "unknown"。
    
    Returns:
        価格帯の分類:
        - "high": 80万円以上
        - "mid": 50万円以上80万円未満
        - "low": 50万円未満
        - "unknown": None または 0以下
    
    Examples:
        100.0 → "high"
        80.0 → "high"
        60.0 → "mid"
        50.0 → "mid"
        30.0 → "low"
        None → "unknown"
        0.0 → "unknown"
    """
    if price is None or price <= 0:
        return "unknown"
    
    if price >= 80.0:
        return "high"
    elif price >= 50.0:
        return "mid"
    else:
        return "low"


def extract_keywords_from_titles(
    rows: list[dict],
    title_column: str = "Title"
) -> dict[str, int]:
    """
    目的: Titleカラムからキーワードを抽出し、出現頻度を集計する（E-2-2-1-2）
    
    Args:
        rows: 行データのリスト（各行はJSONB辞書）
        title_column: Titleカラムの名前（デフォルト: "Title"）
    
    Returns:
        キーワードと出現頻度の辞書
        例: {"Python": 15, "AI": 8, "Next.js": 5, ...}
    
    Notes:
        - 大文字小文字を区別しない（"python" も "Python" も同じ）
        - 部分一致でマッチング（"Pythonエンジニア募集" から "Python" を抽出）
        - 1つのTitleに同じキーワードが複数回出現しても1回としてカウント
    """
    from .keywords import TECH_KEYWORDS
    
    # キーワードの出現頻度を記録
    keyword_freq: dict[str, int] = {}
    
    for row in rows:
        if not isinstance(row, dict):
            continue
        
        title = row.get(title_column)
        if not title or not isinstance(title, str):
            continue
        
        # 小文字化して比較（大文字小文字を区別しない）
        title_lower = title.lower()
        
        # このTitleで既に見つかったキーワードを記録（重複カウント防止）
        found_in_this_title = set()
        
        for keyword in TECH_KEYWORDS:
            keyword_lower = keyword.lower()
            
            # 部分一致でマッチング
            if keyword_lower in title_lower:
                # まだこのTitleで見つかっていない場合のみカウント
                if keyword not in found_in_this_title:
                    keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
                    found_in_this_title.add(keyword)
    
    return keyword_freq


def compare_keywords(
    base_rows: list[dict],
    target_rows: list[dict],
    title_column: str = "Title",
    top_n: int = 10
) -> dict:
    """
    目的: base/targetのキーワード頻度を比較し、増減を返す（E-2-2-1-2）
    
    Args:
        base_rows: 基準データの行データリスト
        target_rows: 比較対象データの行データリスト
        title_column: Titleカラムの名前（デフォルト: "Title"）
        top_n: 増加/減少キーワードのTop数（デフォルト: 10）
    
    Returns:
        {
            "base_total": 153,
            "target_total": 138,
            "increased_keywords": [{"keyword": "AI", "base": 5, "target": 15, "diff": 10}, ...],
            "decreased_keywords": [{"keyword": "PHP", "base": 30, "target": 22, "diff": -8}, ...],
            "new_keywords": ["ChatGPT", "LLM"],
            "disappeared_keywords": ["Flash"]
        }
    """
    # 各データセットのキーワード頻度を取得
    base_freq = extract_keywords_from_titles(base_rows, title_column)
    target_freq = extract_keywords_from_titles(target_rows, title_column)
    
    # すべてのキーワードを取得（base と target の和集合）
    all_keywords = set(base_freq.keys()) | set(target_freq.keys())
    
    # 増加/減少を計算
    changes = []
    for keyword in all_keywords:
        base_count = base_freq.get(keyword, 0)
        target_count = target_freq.get(keyword, 0)
        diff = target_count - base_count
        
        changes.append({
            "keyword": keyword,
            "base": base_count,
            "target": target_count,
            "diff": diff
        })
    
    # 増加キーワード（diff > 0）を抽出してTop N
    increased = [c for c in changes if c["diff"] > 0]
    increased_sorted = sorted(increased, key=lambda x: x["diff"], reverse=True)[:top_n]
    
    # 減少キーワード（diff < 0）を抽出してTop N
    decreased = [c for c in changes if c["diff"] < 0]
    decreased_sorted = sorted(decreased, key=lambda x: x["diff"])[:top_n]
    
    # 新規出現キーワード（baseになくtargetにある）
    new_keywords = [k for k in target_freq.keys() if k not in base_freq]
    
    # 消失キーワード（baseにあってtargetにない）
    disappeared_keywords = [k for k in base_freq.keys() if k not in target_freq]
    
    return {
        "base_total": len(base_rows),
        "target_total": len(target_rows),
        "increased_keywords": increased_sorted,
        "decreased_keywords": decreased_sorted,
        "new_keywords": sorted(new_keywords),
        "disappeared_keywords": sorted(disappeared_keywords)
    }


def compare_price_ranges(
    base_rows: list[dict],
    target_rows: list[dict],
    price_column: str = "UnitPrice"
) -> dict:
    """
    目的: base/targetの価格帯別集計と比較を行う（E-2-2改善タスク1）
    
    Args:
        base_rows: 基準データの行データリスト（各行はJSONB辞書）
        target_rows: 比較対象データの行データリスト（各行はJSONB辞書）
        price_column: 価格カラムの名前（デフォルト: "UnitPrice"）
    
    Returns:
        価格帯別の集計結果と増減:
        {
            "base": {"high": 12, "mid": 45, "low": 96, "unknown": 0},
            "target": {"high": 8, "mid": 52, "low": 78, "unknown": 0},
            "changes": {
                "high": {"diff": -4, "percent": -33.3},
                "mid": {"diff": 7, "percent": 15.6},
                "low": {"diff": -18, "percent": -18.8},
                "unknown": {"diff": 0, "percent": 0.0}
            }
        }
    """
    # 価格帯別の集計を初期化
    base_counts = {"high": 0, "mid": 0, "low": 0, "unknown": 0}
    target_counts = {"high": 0, "mid": 0, "low": 0, "unknown": 0}
    
    # base データの集計
    for row in base_rows:
        if not isinstance(row, dict):
            continue
        
        price_str = row.get(price_column)
        price_value = extract_price_value(price_str)
        price_range = classify_price_range(price_value)
        
        if price_range in base_counts:
            base_counts[price_range] += 1
    
    # target データの集計
    for row in target_rows:
        if not isinstance(row, dict):
            continue
        
        price_str = row.get(price_column)
        price_value = extract_price_value(price_str)
        price_range = classify_price_range(price_value)
        
        if price_range in target_counts:
            target_counts[price_range] += 1
    
    # 増減の計算
    changes = {}
    for range_name in ["high", "mid", "low", "unknown"]:
        base_count = base_counts[range_name]
        target_count = target_counts[range_name]
        diff = target_count - base_count
        
        # 増減率の計算（base が 0 の場合は 0.0）
        if base_count > 0:
            percent = round((diff / base_count) * 100.0, 1)
        else:
            percent = 0.0
        
        changes[range_name] = {
            "diff": diff,
            "percent": percent
        }
    
    return {
        "base": base_counts,
        "target": target_counts,
        "changes": changes
    }

