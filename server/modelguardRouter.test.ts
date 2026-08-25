import { afterEach, describe, expect, it, vi } from "vitest";
import { modelGuardRouter } from "./modelguardRouter";

const originalUrl = process.env.MODELGUARD_API_URL;

afterEach(() => {
  process.env.MODELGUARD_API_URL = originalUrl;
  vi.unstubAllGlobals();
});

describe("modelguard API proxy", () => {
  it("reports preview mode when no FastAPI endpoint is configured", async () => {
    delete process.env.MODELGUARD_API_URL;
    const result = await modelGuardRouter.createCaller({} as never).status();
    expect(result.connected).toBe(false);
  });

  it("proxies configured API health checks", async () => {
    process.env.MODELGUARD_API_URL = "https://modelguard.example/";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 })));
    const result = await modelGuardRouter.createCaller({} as never).status();
    expect(result).toMatchObject({ connected: true, apiUrl: "https://modelguard.example" });
    expect(fetch).toHaveBeenCalledWith("https://modelguard.example/health", expect.any(Object));
  });
});
