import { Link, useParams } from "react-router-dom";

export default function DatasetDetailPage() {
    const { datasetId } = useParams<{ datasetId: string }>();

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif", maxWidth: 1200 }}>
            <h1>Prism - データセット詳細</h1>

            <div style={{ marginTop: 16, marginBottom: 16 }}>
                <Link to="/" style={{ color: "#007bff", textDecoration: "none" }}>
                    ← データセット一覧に戻る
                </Link>
            </div>

            <p>Dataset ID: {datasetId}</p>
            <p style={{ color: "#666" }}>この画面は次のタスク（C-2）で実装予定です。</p>
        </div>
    );
}
