import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { uploadDataset, getDatasets, getDatasetDetail, getDatasetStats, getDatasetAnalysis, compareDatasets, getComparisonAnalysis } from "./datasets";

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

describe("compareDatasets", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("2つのデータセットの統計差分を取得できる", async () => {
        const mockJson = {
            base_dataset: {
                dataset_id: 1,
                filename: "test_base.csv",
                created_at: "2026-01-01T00:00:00Z",
                rows: 100,
            },
            target_dataset: {
                dataset_id: 2,
                filename: "test_target.csv",
                created_at: "2026-01-08T00:00:00Z",
                rows: 105,
            },
            comparison: {
                rows_change: {
                    base: 100,
                    target: 105,
                    diff: 5,
                    percent: 5.0,
                },
                columns_change: [
                    {
                        name: "price",
                        kind: "number",
                        base: { min: 1000, max: 5000, avg: 3000 },
                        target: { min: 1100, max: 5200, avg: 3150 },
                        diff: { min: 100, max: 200, avg: 150 },
                    },
                ],
            },
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await compareDatasets(1, 2, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.comparison.rows_change.diff).toBe(5);
        expect(actual.comparison.columns_change).toHaveLength(1);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/compare?base=1&target=2");
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

        await expect(compareDatasets(1, 999, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Dataset not found");
    });

    it("同一ID指定で400エラーを投げる", async () => {
        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify({ detail: "base and target must be different" }), {
                status: 400,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        await expect(compareDatasets(1, 1, { apiBaseUrl: "http://example.test" })).rejects.toThrow("base and target must be different");
    });
});

describe("getComparisonAnalysis", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("2つのデータセットのLLM推移分析を取得できる", async () => {
        const mockJson = {
            base_dataset: {
                dataset_id: 1,
                filename: "test_base.csv",
                created_at: "2026-01-01T00:00:00Z",
                rows: 100,
            },
            target_dataset: {
                dataset_id: 2,
                filename: "test_target.csv",
                created_at: "2026-01-08T00:00:00Z",
                rows: 105,
            },
            comparison_summary: {
                rows_change: {
                    base: 100,
                    target: 105,
                    diff: 5,
                    percent: 5.0,
                },
                significant_changes: [
                    {
                        column_name: "price",
                        change_type: "avg",
                        base_value: 3000,
                        target_value: 3150,
                        diff: 150,
                        percent: 5.0,
                    },
                ],
            },
            analysis_text: "## 変化の概要\n行数が5件増加しました（5.0%増）。\n\n## 注目すべき変化\npriceカラムの平均値が3000から3150に上昇しています。",
            generated_at: "2026-01-10T12:00:00Z",
        };

        const fetchMock = vi.fn(async () => {
            return new Response(JSON.stringify(mockJson), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
        });
        vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

        const actual = await getComparisonAnalysis(1, 2, { apiBaseUrl: "http://example.test" });

        expect(actual).toEqual(mockJson);
        expect(actual.analysis_text).toContain("変化の概要");
        expect(actual.comparison_summary.significant_changes).toHaveLength(1);
        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        expect(url).toBe("http://example.test/datasets/compare/analysis?base=1&target=2");
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

        await expect(getComparisonAnalysis(1, 999, { apiBaseUrl: "http://example.test" })).rejects.toThrow("Dataset not found");
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

        await expect(getComparisonAnalysis(1, 2, { apiBaseUrl: "http://example.test" })).rejects.toThrow("HTTP 504");
    });
});
