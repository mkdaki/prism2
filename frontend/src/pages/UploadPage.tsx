import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { uploadDataset, type UploadDatasetResponse } from "../api/datasets";

export default function UploadPage() {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [result, setResult] = useState<UploadDatasetResponse | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const navigate = useNavigate();

    const canUpload = useMemo(() => {
        return selectedFile !== null && !isUploading;
    }, [selectedFile, isUploading]);

    async function handleUploadClick(): Promise<void> {
        /** 目的: 選択されたCSVをアップロードし、結果を画面に反映する。 */
        if (!selectedFile) {
            alert("CSVファイルを選択してください。");
            return;
        }

        setIsUploading(true);
        setResult(null);
        setErrorMessage(null);
        try {
            const response = await uploadDataset(selectedFile);
            setResult(response);
        } catch (e) {
            const message = e instanceof Error ? e.message : "アップロードに失敗しました。";
            setErrorMessage(message);
            alert(message);
        } finally {
            setIsUploading(false);
        }
    }

    function handleViewList(): void {
        navigate("/");
    }

    return (
        <div style={{ padding: 16, fontFamily: "sans-serif", maxWidth: 720 }}>
            <h1>Prism - CSVアップロード</h1>

            <div style={{ marginTop: 16, marginBottom: 16 }}>
                <Link to="/" style={{ color: "#007bff", textDecoration: "none" }}>
                    ← データセット一覧に戻る
                </Link>
            </div>

            <section style={{ marginTop: 16 }}>
                <h2>CSVアップロード</h2>

                <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                    <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(e) => {
                            const file = e.target.files?.[0] ?? null;
                            setSelectedFile(file);
                        }}
                    />

                    <button type="button" onClick={handleUploadClick} disabled={!canUpload}>
                        {isUploading ? "アップロード中..." : "アップロード"}
                    </button>
                </div>

                {selectedFile ? (
                    <p style={{ marginTop: 8 }}>
                        選択中: <strong>{selectedFile.name}</strong>
                    </p>
                ) : (
                    <p style={{ marginTop: 8, color: "#666" }}>CSVファイルを選択してください。</p>
                )}

                {result ? (
                    <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
                        <h3 style={{ marginTop: 0 }}>アップロード成功</h3>
                        <p style={{ margin: 0 }}>
                            dataset_id: <strong>{result.dataset_id}</strong>
                        </p>
                        <p style={{ margin: 0 }}>
                            rows: <strong>{result.rows}</strong>
                        </p>
                        <p style={{ margin: 0 }}>
                            filename: <strong>{result.filename}</strong>
                        </p>
                        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                            <button type="button" onClick={handleViewList} style={{ padding: "8px 16px", background: "#28a745", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
                                一覧を見る
                            </button>
                            <Link to={`/datasets/${result.dataset_id}`} style={{ padding: "8px 16px", background: "#007bff", color: "#fff", textDecoration: "none", borderRadius: 4, display: "inline-block" }}>
                                詳細を見る
                            </Link>
                        </div>
                    </div>
                ) : null}

                {errorMessage ? (
                    <div style={{ marginTop: 12, padding: 12, border: "1px solid #f2b8b5", borderRadius: 8, background: "#fff5f5" }}>
                        <h3 style={{ marginTop: 0, color: "#a61b1b" }}>エラー</h3>
                        <p style={{ margin: 0 }}>{errorMessage}</p>
                    </div>
                ) : null}
            </section>
        </div>
    );
}
