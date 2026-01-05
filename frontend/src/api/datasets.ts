export type UploadDatasetResponse = {
    dataset_id: number;
    rows: number;
    filename: string;
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

    const fromProcessEnv = typeof process !== "undefined" ? process.env.VITE_API_BASE_URL : undefined;
    if (typeof fromProcessEnv === "string" && fromProcessEnv.trim()) {
        return fromProcessEnv.trim().replace(/\/+$/, "");
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


