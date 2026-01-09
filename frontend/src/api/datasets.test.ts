import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { uploadDataset, getDatasets } from "./datasets";

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

