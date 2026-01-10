import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { uploadDataset, getDatasets, getDatasetDetail, getDatasetStats, getDatasetAnalysis } from "./datasets";

describe("uploadDataset", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("成功時にレスポンスJSONを返す", async () => {
        const file = new File(["colA\n1\n"], "sample.csv", { type: "text/csv" });
        const mockJson = { dataset_id: 123, rows: 2, filename: "sample.csv" };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await uploadDataset(file, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/upload");
        expect(init.method).toBe("POST");
        expect(init.body).toBeInstanceOf(FormData);
        expect((init.body as FormData).get("file")).toBe(file);
    });

    it("失敗時にdetailを含むエラーを投げる", async () => {
        const file = new File(["x"], "sample.csv", { type: "text/csv" });

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "Only .csv is supported" }), {
                status: 400,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(uploadDataset(file, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Only .csv is supported");
    });
});

describe("getDatasets", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("データセット一覧を取得できる（0件）", async () => {
        const mockJson = { datasets: [] };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getDatasets({ apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.datasets).toHaveLength(0);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets");
        expect(init.method).toBe("GET");
    });

    it("データセット一覧を取得できる（複数件）", async () => {
        const mockJson = {
            datasets: [
                { dataset_id: 1, filename: "test1.csv", created_at: "2026-01-01T00:00:00Z", row_count: 10 },
                { dataset_id: 2, filename: "test2.csv", created_at: "2026-01-02T00:00:00Z", row_count: 20 },
            ],
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getDatasets({ apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.datasets).toHaveLength(2);
        expect(actual.datasets[0].dataset_id).toBe(1);
        expect(actual.datasets[0].filename).toBe("test1.csv");
        expect(actual.datasets[0].row_count).toBe(10);
        expect(actual.datasets[1].dataset_id).toBe(2);
    });

    it("失敗時にエラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "Internal Server Error" }), {
                status: 500,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(getDatasets({ apiBaseUrl: "http://example.test" })).rejects.toThrow("Internal Server Error");
    });
});

describe("getDatasetDetail", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("データセット詳細を取得できる", async () => {
        const mockJson = {
            dataset_id: 1,
            filename: "test.csv",
            created_at: "2026-01-01T00:00:00Z",
            rows: 100,
            samples: [
                { row_index: 0, data: { col1: "value1", col2: "value2" } },
                { row_index: 1, data: { col1: "value3", col2: "value4" } },
            ],
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getDatasetDetail(1, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.dataset_id).toBe(1);
        expect(actual.samples).toHaveLength(2);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/1");
        expect(init.method).toBe("GET");
    });

    it("存在しないIDで404エラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "Dataset not found" }), {
                status: 404,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(getDatasetDetail(999, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Dataset not found");
    });
});

describe("getDatasetStats", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("データセット統計を取得できる", async () => {
        const mockJson = {
            dataset_id: 1,
            rows: 100,
            columns: [
                {
                    name: "col1",
                    kind: "number" as const,
                    present_count: 100,
                    non_empty_count: 95,
                    numeric: { count: 95, min: 1.0, max: 100.0, avg: 50.5 },
                    top_values: null,
                },
                {
                    name: "col2",
                    kind: "string" as const,
                    present_count: 100,
                    non_empty_count: 90,
                    numeric: null,
                    top_values: [
                        { value: "A", count: 30 },
                        { value: "B", count: 25 },
                    ],
                },
            ],
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getDatasetStats(1, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.columns).toHaveLength(2);
        expect(actual.columns[0].kind).toBe("number");
        expect(actual.columns[0].numeric?.avg).toBe(50.5);
        expect(actual.columns[1].kind).toBe("string");
        expect(actual.columns[1].top_values).toHaveLength(2);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/1/stats");
        expect(init.method).toBe("GET");
    });

    it("存在しないIDで404エラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "Dataset not found" }), {
                status: 404,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(getDatasetStats(999, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Dataset not found");
    });
});

describe("getDatasetAnalysis", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("データセット分析を取得できる", async () => {
        const mockJson = {
            dataset_id: 1,
            generated_at: "2026-01-10T12:00:00Z",
            analysis_text: "このデータセットには100行のデータが含まれています。\n\n注目点：\n- col1は数値型で平均50.5です。",
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getDatasetAnalysis(1, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.dataset_id).toBe(1);
        expect(actual.analysis_text).toContain("注目点");
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/1/analysis");
        expect(init.method).toBe("GET");
    });

    it("存在しないIDで404エラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "Dataset not found" }), {
                status: 404,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(getDatasetAnalysis(999, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Dataset not found");
    });

    it("LLMエラー時に適切なエラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(
                JSON.stringify({
                    detail: {
                        error: {
                            code: "LLM_TIMEOUT",
                            message: "LLM request timed out",
                            retryable: true,
                        },
                    },
                }),
                {
                    status: 504,
                    statusText: "Gateway Timeout",
                    headers: { "Content-Type": "application/json" },
                }
            );
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(getDatasetAnalysis(1, { apiBaseUrl: "http://example.test" })).rejects.toThrow("HTTP 504");
    });
});
