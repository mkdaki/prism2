import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
    getDatasetDetail,
    getDatasetStats,
    getDatasetAnalysis,
    type DatasetDetail,
    type DatasetStats,
    type DatasetAnalysis,
} from "../api/datasets";

export default function DatasetDetailPage() {
    const { datasetId } = useParams<{ datasetId: string }>();

    const [detail, setDetail] = useState<DatasetDetail | null>(null);
    const [stats, setStats] = useState<DatasetStats | null>(null);
    const [analysis, setAnalysis] = useState<DatasetAnalysis | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!datasetId) {
                setError("データセットIDが指定されていません");
                setLoading(false);
                return;
            }

            const id = parseInt(datasetId, 10);
            if (isNaN(id)) {
                setError("無効なデータセットIDです");
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setError(null);

                // 3つのAPIを並行で呼び出す
                const [detailData, statsData, analysisData] = await Promise.all([
                    getDatasetDetail(id),
                    getDatasetStats(id),
                    getDatasetAnalysis(id),
                ]);

                setDetail(detailData);
                setStats(statsData);
                setAnalysis(analysisData);
            } catch (err) {
                const message = err instanceof Error ? err.message : "データの取得に失敗しました";
                setError(message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [datasetId]);

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif", maxWidth: 1200 }}>
            <h1>Prism - データセット詳細</h1>

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

            {!loading && !error && detail && (
                <>
                    {/* メタ情報セクション */}
                    <section style={{ marginBottom: 32 }}>
                        <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>メタ情報</h2>
                        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
                            <tbody>
                                <tr style={{ borderBottom: "1px solid #ddd" }}>
                                    <th style={{ padding: 8, textAlign: "left", width: 200, backgroundColor: "#f5f5f5" }}>
                                        データセットID
                                    </th>
                                    <td style={{ padding: 8 }}>{detail.dataset_id}</td>
                                </tr>
                                <tr style={{ borderBottom: "1px solid #ddd" }}>
                                    <th style={{ padding: 8, textAlign: "left", backgroundColor: "#f5f5f5" }}>ファイル名</th>
                                    <td style={{ padding: 8 }}>{detail.filename}</td>
                                </tr>
                                <tr style={{ borderBottom: "1px solid #ddd" }}>
                                    <th style={{ padding: 8, textAlign: "left", backgroundColor: "#f5f5f5" }}>作成日時</th>
                                    <td style={{ padding: 8 }}>{new Date(detail.created_at).toLocaleString("ja-JP")}</td>
                                </tr>
                                <tr style={{ borderBottom: "1px solid #ddd" }}>
                                    <th style={{ padding: 8, textAlign: "left", backgroundColor: "#f5f5f5" }}>行数</th>
                                    <td style={{ padding: 8 }}>{detail.rows.toLocaleString()} 行</td>
                                </tr>
                            </tbody>
                        </table>
                    </section>

                    {/* サンプルデータセクション */}
                    <section style={{ marginBottom: 32 }}>
                        <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>サンプルデータ（先頭10行）</h2>
                        {detail.samples.length === 0 ? (
                            <p style={{ color: "#666", marginTop: 16 }}>サンプルデータがありません</p>
                        ) : (
                            <div style={{ overflowX: "auto", marginTop: 16 }}>
                                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                                    <thead>
                                        <tr style={{ backgroundColor: "#f5f5f5" }}>
                                            <th style={{ padding: 8, border: "1px solid #ddd", textAlign: "left" }}>行番号</th>
                                            {detail.samples[0] &&
                                                Object.keys(detail.samples[0].data).map((key) => (
                                                    <th
                                                        key={key}
                                                        style={{ padding: 8, border: "1px solid #ddd", textAlign: "left" }}
                                                    >
                                                        {key}
                                                    </th>
                                                ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {detail.samples.map((sample) => (
                                            <tr key={sample.row_index}>
                                                <td style={{ padding: 8, border: "1px solid #ddd" }}>{sample.row_index}</td>
                                                {Object.values(sample.data).map((value, idx) => (
                                                    <td key={idx} style={{ padding: 8, border: "1px solid #ddd" }}>
                                                        {String(value ?? "")}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>

                    {/* 統計情報セクション */}
                    {stats && (
                        <section style={{ marginBottom: 32 }}>
                            <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>統計情報</h2>
                            <p style={{ marginTop: 16, color: "#666" }}>
                                カラム数: {stats.columns.length} / 行数: {stats.rows.toLocaleString()}
                            </p>
                            <div style={{ marginTop: 16 }}>
                                {stats.columns.map((col) => (
                                    <div
                                        key={col.name}
                                        style={{
                                            marginBottom: 16,
                                            padding: 16,
                                            backgroundColor: "#f9f9f9",
                                            borderRadius: 4,
                                            border: "1px solid #ddd",
                                        }}
                                    >
                                        <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                                            {col.name}{" "}
                                            <span
                                                style={{
                                                    fontSize: 12,
                                                    padding: "2px 8px",
                                                    backgroundColor: getKindColor(col.kind),
                                                    color: "#fff",
                                                    borderRadius: 3,
                                                    marginLeft: 8,
                                                }}
                                            >
                                                {col.kind}
                                            </span>
                                        </h3>
                                        <p style={{ margin: "4px 0", fontSize: 14, color: "#666" }}>
                                            存在: {col.present_count} / 非空: {col.non_empty_count}
                                        </p>
                                        {col.numeric && (
                                            <div style={{ marginTop: 8, fontSize: 14 }}>
                                                <strong>数値統計:</strong> 件数={col.numeric.count}, 最小=
                                                {col.numeric.min.toFixed(2)}, 最大={col.numeric.max.toFixed(2)}, 平均=
                                                {col.numeric.avg.toFixed(2)}
                                            </div>
                                        )}
                                        {col.top_values && col.top_values.length > 0 && (
                                            <div style={{ marginTop: 8, fontSize: 14 }}>
                                                <strong>頻出値:</strong>
                                                <ul style={{ margin: "4px 0", paddingLeft: 20 }}>
                                                    {col.top_values.map((tv, idx) => (
                                                        <li key={idx}>
                                                            {tv.value} ({tv.count}件)
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* LLM分析結果セクション */}
                    {analysis && (
                        <section style={{ marginBottom: 32 }}>
                            <h2 style={{ borderBottom: "2px solid #333", paddingBottom: 8 }}>分析結果</h2>
                            <p style={{ fontSize: 12, color: "#999", marginTop: 8 }}>
                                生成日時: {new Date(analysis.generated_at).toLocaleString("ja-JP")}
                            </p>
                            <div
                                style={{
                                    marginTop: 16,
                                    padding: 16,
                                    backgroundColor: "#f0f8ff",
                                    borderRadius: 4,
                                    border: "1px solid #b3d9ff",
                                    whiteSpace: "pre-wrap",
                                    lineHeight: 1.6,
                                }}
                            >
                                {analysis.analysis_text}
                            </div>
                        </section>
                    )}
                </>
            )}
        </div>
    );
}

function getKindColor(kind: string): string {
    switch (kind) {
        case "number":
            return "#2196f3";
        case "string":
            return "#4caf50";
        case "mixed":
            return "#ff9800";
        case "empty":
            return "#9e9e9e";
        default:
            return "#757575";
    }
}
