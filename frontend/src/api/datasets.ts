export type UploadDatasetResponse = {
    dataset_id: number;
    rows: number;
    filename: string;
};

export type Dataset = {
    dataset_id: number;
    filename: string;
    created_at: string;
    row_count: number;
};

export type GetDatasetsResponse = {
    datasets: Dataset[];
};

export type DatasetDetail = {
    dataset_id: number;
    filename: string;
    created_at: string;
    rows: number;
    samples: Array<{
        row_index: number;
        data: Record<string, unknown>;
    }>;
};

export type DatasetStats = {
    dataset_id: number;
    rows: number;
    columns: Array<{
        name: string;
        kind: "number" | "string" | "mixed" | "empty";
        present_count: number;
        non_empty_count: number;
        numeric: {
            count: number;
            min: number;
            max: number;
            avg: number;
        } | null;
        top_values: Array<{
            value: string;
            count: number;
        }> | null;
    }>;
};

export type DatasetAnalysis = {
    dataset_id: number;
    generated_at: string;
    analysis_text: string;
};

export type DatasetComparisonResponse = {
    base_dataset: {
        dataset_id: number;
        filename: string;
        created_at: string;
        rows: number;
    };
    target_dataset: {
        dataset_id: number;
        filename: string;
        created_at: string;
        rows: number;
    };
    comparison: {
        rows_change: {
            base: number;
            target: number;
            diff: number;
            percent: number;
        };
        columns_change: Array<{
            name: string;
            kind: string;
            base: Record<string, number> | null;
            target: Record<string, number> | null;
            diff: Record<string, number> | null;
        }>;
    };
};

export type ComparisonAnalysisResponse = {
    base_dataset: {
        dataset_id: number;
        filename: string;
        created_at: string;
        rows: number;
    };
    target_dataset: {
        dataset_id: number;
        filename: string;
        created_at: string;
        rows: number;
    };
    comparison_summary: {
        rows_change: {
            base: number;
            target: number;
            diff: number;
            percent: number;
        };
        significant_changes: Array<{
            column_name: string;
            change_type: string;
            base_value: number;
            target_value: number;
            diff: number;
            percent: number;
        }>;
    };
    analysis_text: string;
    generated_at: string;
};

export type UploadDatasetOptions = {
    apiBaseUrl?: string;
    signal?: AbortSignal;
};

function getApiBaseUrl(options?: UploadDatasetOptions): string {
    const fromOptions = options?.apiBaseUrl;
    if (fromOptions && fromOptions.trim()) {
        return fromOptions.trim().replace(/\/+$/, "");
    }

    const fromViteEnv = (import.meta as unknown as { env?: Record<string, unknown> }).env?.VITE_API_BASE_URL;
    if (typeof fromViteEnv === "string" && fromViteEnv.trim()) {
        return fromViteEnv.trim().replace(/\/+$/, "");
    }

    return "http://localhost:8001";
}

async function parseErrorDetail(response: Response): Promise<string> {
    try {
        const body = await response.json();
        const detail = (body as { detail?: unknown }).detail;
        if (typeof detail === "string" && detail.trim()) {
            return detail;
        }
    } catch {
        // ignore JSON parse errors
    }
    return `HTTP ${response.status} ${response.statusText}`.trim();
}

export async function uploadDataset(file: File, options?: UploadDatasetOptions): Promise<UploadDatasetResponse> {
    /** 目的: CSVファイルを `POST /datasets/upload` へ送信し、結果を返す。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${apiBaseUrl}/datasets/upload`, {
        method: "POST",
        body: formData,
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as UploadDatasetResponse;
    return json;
}

export async function getDatasets(options?: UploadDatasetOptions): Promise<GetDatasetsResponse> {
    /** 目的: `GET /datasets` からデータセット一覧を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as GetDatasetsResponse;
    return json;
}

export async function getDatasetDetail(datasetId: number, options?: UploadDatasetOptions): Promise<DatasetDetail> {
    /** 目的: `GET /datasets/{dataset_id}` からデータセット詳細を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/${datasetId}`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as DatasetDetail;
    return json;
}

export async function getDatasetStats(datasetId: number, options?: UploadDatasetOptions): Promise<DatasetStats> {
    /** 目的: `GET /datasets/{dataset_id}/stats` からデータセット統計を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/${datasetId}/stats`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as DatasetStats;
    return json;
}

export async function getDatasetAnalysis(datasetId: number, options?: UploadDatasetOptions): Promise<DatasetAnalysis> {
    /** 目的: `GET /datasets/{dataset_id}/analysis` からデータセット分析を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/${datasetId}/analysis`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as DatasetAnalysis;
    return json;
}

export async function compareDatasets(baseId: number, targetId: number, options?: UploadDatasetOptions): Promise<DatasetComparisonResponse> {
    /** 目的: `GET /datasets/compare` から2つのデータセットの統計差分を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/compare?base=${baseId}&target=${targetId}`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as DatasetComparisonResponse;
    return json;
}

export async function getComparisonAnalysis(baseId: number, targetId: number, options?: UploadDatasetOptions): Promise<ComparisonAnalysisResponse> {
    /** 目的: `GET /datasets/compare/analysis` から2つのデータセットのLLM推移分析を取得する。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/compare/analysis?base=${baseId}&target=${targetId}`, {
        method: "GET",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    const json = (await response.json()) as ComparisonAnalysisResponse;
    return json;
}

export async function deleteDataset(datasetId: number, options?: UploadDatasetOptions): Promise<void> {
    /** 目的: `DELETE /datasets/{dataset_id}` でデータセットを削除する（E-1-1）。 */
    const apiBaseUrl = getApiBaseUrl(options);

    const response = await fetch(`${apiBaseUrl}/datasets/${datasetId}`, {
        method: "DELETE",
        signal: options?.signal,
    });

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new Error(detail);
    }

    // 204 No Content なので何も返さない
}
