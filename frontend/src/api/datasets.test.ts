import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { uploadDataset } from "./datasets";

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


