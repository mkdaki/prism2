import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDatasets, type Dataset } from "../api/datasets";

export default function DatasetListPage() {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    useEffect(() => {
        async function fetchDatasets(): Promise<void> {
            setIsLoading(true);
            setErrorMessage(null);
            try {
                const response = await getDatasets();
                setDatasets(response.datasets);
            } catch (e) {
                const message = e instanceof Error ? e.message : "データセット一覧の取得に失敗しました。";
                setErrorMessage(message);
            } finally {
                setIsLoading(false);
            }
        }

        fetchDatasets();
    }, []);

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif", maxWidth: 1200 }}>
            <h1>Prism - データセット一覧</h1>

            <div style={{ marginTop: 16, marginBottom: 16 }}>
                <Link to="/upload" style={{ padding: "8px 16px", background: "#007bff", color: "#fff", textDecoration: "none", borderRadius: 4, display: "inline-block" }}>
                    CSVをアップロード
                </Link>
            </div>

            {isLoading ? (
                <p>読み込み中...</p>
            ) : errorMessage ? (
                <div style={{ marginTop: 12, padding: 12, border: "1px solid #f2b8b5", borderRadius: 8, background: "#fff5f5" }}>
                    <h3 style={{ marginTop: 0, color: "#a61b1b" }}>エラー</h3>
                    <p style={{ margin: 0 }}>{errorMessage}</p>
                </div>
            ) : datasets.length === 0 ? (
                <p style={{ color: "#666" }}>データセットがまだありません。CSVをアップロードしてください。</p>
            ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
                    <thead>
                        <tr style={{ background: "#f5f5f5", borderBottom: "2px solid #ddd" }}>
                            <th style={{ padding: 12, textAlign: "left" }}>ID</th>
                            <th style={{ padding: 12, textAlign: "left" }}>ファイル名</th>
                            <th style={{ padding: 12, textAlign: "left" }}>行数</th>
                            <th style={{ padding: 12, textAlign: "left" }}>作成日時</th>
                            <th style={{ padding: 12, textAlign: "left" }}>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {datasets.map((dataset) => (
                            <tr key={dataset.dataset_id} style={{ borderBottom: "1px solid #eee" }}>
                                <td style={{ padding: 12 }}>{dataset.dataset_id}</td>
                                <td style={{ padding: 12 }}>{dataset.filename}</td>
                                <td style={{ padding: 12 }}>{dataset.row_count}</td>
                                <td style={{ padding: 12 }}>{new Date(dataset.created_at).toLocaleString("ja-JP")}</td>
                                <td style={{ padding: 12 }}>
                                    <Link to={`/datasets/${dataset.dataset_id}`} style={{ color: "#007bff", textDecoration: "none" }}>
                                        詳細を見る
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}
