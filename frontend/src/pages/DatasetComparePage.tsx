import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
    compareDatasets,
    getComparisonAnalysis,
    type DatasetComparisonResponse,
    type ComparisonAnalysisResponse,
} from "../api/datasets";

export default function DatasetComparePage() {
    const [searchParams] = useSearchParams();
    const baseId = Number(searchParams.get("base"));
    const targetId = Number(searchParams.get("target"));

    const [comparison, setComparison] = useState<DatasetComparisonResponse | null>(null);
    const [analysis, setAnalysis] = useState<ComparisonAnalysisResponse | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!baseId || !targetId || isNaN(baseId) || isNaN(targetId)) {
                setError("無効なデータセットIDが指定されています");
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setError(null);

                // 2つのAPIを並行で呼び出す
                const [comparisonData, analysisData] = await Promise.all([
                    compareDatasets(baseId, targetId),
                    getComparisonAnalysis(baseId, targetId),
                ]);

                setComparison(comparisonData);
                setAnalysis(analysisData);
            } catch (err) {
                const message = err instanceof Error ? err.message : "データの取得に失敗しました";
                setError(message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [baseId, targetId]);

    const formatPercent = (value: number): string => {
        const sign = value > 0 ? "+" : "";
        return `${sign}${value.toFixed(1)}%`;
    };

    const getChangeColor = (value: number): string => {
        if (value > 0) return "#4caf50"; // 緑（増加）
        if (value < 0) return "#f44336"; // 赤（減少）
        return "#666"; // グレー（変化なし）
    };

    const copyToClipboard = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            alert("クリップボードにコピーしました");
        } catch (err) {
            alert("コピーに失敗しました");
        }
    };

    const exportComparisonAsMarkdown = () => {
        if (!comparison || !analysis) return;

        const date = new Date().toISOString().split("T")[0].replace(/-/g, "");
        const filename = `comparison_${baseId}_${targetId}_${date}.md`;

        // 統計差分サマリーを作成
        let statsSummary = "### 統計差分\n\n";
        statsSummary += `#### 行数変化\n\n`;
        statsSummary += `- 基準: ${comparison.comparison.rows_change.base}件\n`;
        statsSummary += `- 比較: ${comparison.comparison.rows_change.target}件\n`;
        statsSummary += `- 差分: ${comparison.comparison.rows_change.diff > 0 ? "+" : ""}${
            comparison.comparison.rows_change.diff
        }件 (${formatPercent(comparison.comparison.rows_change.percent)})\n\n`;

        statsSummary += `#### カラムごとの変化\n\n`;
        comparison.comparison.columns_change.forEach((col) => {
            statsSummary += `- **${col.name}** (${col.kind})\n`;
            if (col.kind === "number" && col.base && col.target && col.diff) {
                statsSummary += `  - 基準: min=${col.base.min}, avg=${col.base.avg.toFixed(1)}, max=${col.base.max}\n`;
                statsSummary += `  - 比較: min=${col.target.min}, avg=${col.target.avg.toFixed(1)}, max=${col.target.max}\n`;
                statsSummary += `  - 差分: min=${col.diff.min > 0 ? "+" : ""}${col.diff.min.toFixed(
                    1
                )}, avg=${col.diff.avg > 0 ? "+" : ""}${col.diff.avg.toFixed(1)}, max=${col.diff.max > 0 ? "+" : ""}${col.diff.max.toFixed(
                    1
                )}\n`;
            }
        });

        const content = `# 推移比較分析結果

## 基準データ

- データセットID: ${comparison.base_dataset.dataset_id}
- ファイル名: ${comparison.base_dataset.filename}
- 作成日時: ${new Date(comparison.base_dataset.created_at).toLocaleString("ja-JP")}
- 行数: ${comparison.base_dataset.rows}件

## 比較対象データ

- データセットID: ${comparison.target_dataset.dataset_id}
- ファイル名: ${comparison.target_dataset.filename}
- 作成日時: ${new Date(comparison.target_dataset.created_at).toLocaleString("ja-JP")}
- 行数: ${comparison.target_dataset.rows}件

${statsSummary}

## LLM推移分析

生成日時: ${new Date(analysis.generated_at).toLocaleString("ja-JP")}

${analysis.analysis_text}
`;

        const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif", maxWidth: 1200 }}>
            <h1>Prism - 推移比較</h1>

            <div style={{ marginTop: 16, marginBottom: 16 }}>
                <Link to="/" style={{ color: "#007bff", textDecoration: "none" }}>
                    ← データセット一覧に戻る
                </Link>
            </div>

            {loading && <p>読み込み中...</p>}

            {error && (
                <div style={{ padding: 16, backgroundColor: "#ffebee", color: "#c62828", borderRadius: 4 }}>
                    <strong>エラー:</strong> {error}
                </div>
            )}

            {!loading && !error && comparison && analysis && (
                <>
                    {/* セクション1: メタ情報（横並び） */}
                    <section style={{ marginBottom: 32 }}>
                        <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>比較データセット</h2>
                        <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
                            {/* 基準データ */}
                            <div style={{ flex: 1, padding: 16, backgroundColor: "#e3f2fd", borderRadius: 8 }}>
                                <h3 style={{ marginTop: 0, color: "#1976d2" }}>基準データ</h3>
                                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                                    <tbody>
                                        <tr style={{ borderBottom: "1px solid #90caf9" }}>
                                            <th style={{ padding: 8, textAlign: "left", width: 120 }}>ID</th>
                                            <td style={{ padding: 8 }}>{comparison.base_dataset.dataset_id}</td>
                                        </tr>
                                        <tr style={{ borderBottom: "1px solid #90caf9" }}>
                                            <th style={{ padding: 8, textAlign: "left" }}>ファイル名</th>
                                            <td style={{ padding: 8 }}>{comparison.base_dataset.filename}</td>
                                        </tr>
                                        <tr style={{ borderBottom: "1px solid #90caf9" }}>
                                            <th style={{ padding: 8, textAlign: "left" }}>作成日時</th>
                                            <td style={{ padding: 8 }}>
                                                {new Date(comparison.base_dataset.created_at).toLocaleString("ja-JP")}
                                            </td>
                                        </tr>
                                        <tr>
                                            <th style={{ padding: 8, textAlign: "left" }}>行数</th>
                                            <td style={{ padding: 8 }}>{comparison.base_dataset.rows}件</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            {/* 比較対象データ */}
                            <div style={{ flex: 1, padding: 16, backgroundColor: "#fff3e0", borderRadius: 8 }}>
                                <h3 style={{ marginTop: 0, color: "#f57c00" }}>比較対象データ</h3>
                                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                                    <tbody>
                                        <tr style={{ borderBottom: "1px solid #ffcc80" }}>
                                            <th style={{ padding: 8, textAlign: "left", width: 120 }}>ID</th>
                                            <td style={{ padding: 8 }}>{comparison.target_dataset.dataset_id}</td>
                                        </tr>
                                        <tr style={{ borderBottom: "1px solid #ffcc80" }}>
                                            <th style={{ padding: 8, textAlign: "left" }}>ファイル名</th>
                                            <td style={{ padding: 8 }}>{comparison.target_dataset.filename}</td>
                                        </tr>
                                        <tr style={{ borderBottom: "1px solid #ffcc80" }}>
                                            <th style={{ padding: 8, textAlign: "left" }}>作成日時</th>
                                            <td style={{ padding: 8 }}>
                                                {new Date(comparison.target_dataset.created_at).toLocaleString("ja-JP")}
                                            </td>
                                        </tr>
                                        <tr>
                                            <th style={{ padding: 8, textAlign: "left" }}>行数</th>
                                            <td style={{ padding: 8 }}>{comparison.target_dataset.rows}件</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    {/* セクション2: 統計差分 */}
                    <section style={{ marginBottom: 32 }}>
                        <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>統計差分</h2>

                        {/* 行数変化 */}
                        <div style={{ marginTop: 16, padding: 16, backgroundColor: "#f5f5f5", borderRadius: 8 }}>
                            <h3 style={{ marginTop: 0 }}>行数変化</h3>
                            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                                <span style={{ fontSize: 18 }}>
                                    {comparison.comparison.rows_change.base}件 → {comparison.comparison.rows_change.target}件
                                </span>
                                <span
                                    style={{
                                        fontSize: 24,
                                        fontWeight: "bold",
                                        color: getChangeColor(comparison.comparison.rows_change.diff),
                                    }}
                                >
                                    {comparison.comparison.rows_change.diff > 0 ? "+" : ""}
                                    {comparison.comparison.rows_change.diff}件
                                </span>
                                <span
                                    style={{
                                        fontSize: 18,
                                        color: getChangeColor(comparison.comparison.rows_change.percent),
                                    }}
                                >
                                    ({formatPercent(comparison.comparison.rows_change.percent)})
                                </span>
                            </div>
                        </div>

                        {/* カラムごとの変化 */}
                        <div style={{ marginTop: 16 }}>
                            <h3>カラムごとの変化</h3>
                            {comparison.comparison.columns_change.length === 0 ? (
                                <p style={{ color: "#666" }}>カラムの変化はありません。</p>
                            ) : (
                                <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
                                    <thead>
                                        <tr style={{ backgroundColor: "#f5f5f5", borderBottom: "2px solid #ddd" }}>
                                            <th style={{ padding: 12, textAlign: "left" }}>カラム名</th>
                                            <th style={{ padding: 12, textAlign: "left" }}>種類</th>
                                            <th style={{ padding: 12, textAlign: "left" }}>基準値</th>
                                            <th style={{ padding: 12, textAlign: "left" }}>比較値</th>
                                            <th style={{ padding: 12, textAlign: "left" }}>差分</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {comparison.comparison.columns_change.map((col, idx) => {
                                            const isNumber = col.kind === "number";
                                            return (
                                                <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                                                    <td style={{ padding: 12 }}>{col.name}</td>
                                                    <td style={{ padding: 12 }}>
                                                        <span
                                                            style={{
                                                                padding: "4px 8px",
                                                                borderRadius: 4,
                                                                backgroundColor:
                                                                    col.kind === "number"
                                                                        ? "#e3f2fd"
                                                                        : col.kind === "string"
                                                                        ? "#e8f5e9"
                                                                        : "#fff3e0",
                                                                fontSize: 12,
                                                            }}
                                                        >
                                                            {col.kind}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: 12 }}>
                                                        {isNumber && col.base
                                                            ? `min: ${col.base.min}, avg: ${col.base.avg.toFixed(
                                                                  1
                                                              )}, max: ${col.base.max}`
                                                            : "—"}
                                                    </td>
                                                    <td style={{ padding: 12 }}>
                                                        {isNumber && col.target
                                                            ? `min: ${col.target.min}, avg: ${col.target.avg.toFixed(
                                                                  1
                                                              )}, max: ${col.target.max}`
                                                            : "—"}
                                                    </td>
                                                    <td style={{ padding: 12 }}>
                                                        {isNumber && col.diff ? (
                                                            <div>
                                                                <div
                                                                    style={{
                                                                        color: getChangeColor(col.diff.avg),
                                                                        fontWeight: "bold",
                                                                    }}
                                                                >
                                                                    avg: {col.diff.avg > 0 ? "+" : ""}
                                                                    {col.diff.avg.toFixed(1)}
                                                                </div>
                                                                <div style={{ fontSize: 12, color: "#666" }}>
                                                                    min: {col.diff.min > 0 ? "+" : ""}
                                                                    {col.diff.min.toFixed(1)}, max:{" "}
                                                                    {col.diff.max > 0 ? "+" : ""}
                                                                    {col.diff.max.toFixed(1)}
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            "—"
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </section>

                    {/* セクション3: LLM推移分析結果 */}
                    <section style={{ marginBottom: 32 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8, margin: 0 }}>LLM推移分析</h2>
                            <div style={{ display: "flex", gap: 8 }}>
                                <button
                                    onClick={() => copyToClipboard(analysis.analysis_text)}
                                    style={{
                                        padding: "8px 16px",
                                        backgroundColor: "#2196f3",
                                        color: "#fff",
                                        border: "none",
                                        borderRadius: 4,
                                        cursor: "pointer",
                                        fontSize: 14,
                                    }}
                                >
                                    📋 コピー
                                </button>
                                <button
                                    onClick={exportComparisonAsMarkdown}
                                    style={{
                                        padding: "8px 16px",
                                        backgroundColor: "#ff9800",
                                        color: "#fff",
                                        border: "none",
                                        borderRadius: 4,
                                        cursor: "pointer",
                                        fontSize: 14,
                                    }}
                                >
                                    📄 Markdownでエクスポート
                                </button>
                            </div>
                        </div>
                        <div
                            style={{
                                marginTop: 16,
                                padding: 16,
                                backgroundColor: "#f9f9f9",
                                borderRadius: 8,
                                whiteSpace: "pre-wrap",
                                lineHeight: 1.6,
                            }}
                        >
                            {analysis.analysis_text}
                        </div>
                        <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                            生成日時: {new Date(analysis.generated_at).toLocaleString("ja-JP")}
                        </div>
                    </section>
                </>
            )}
        </div>
    );
}
