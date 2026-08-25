import { z } from "zod";
import { publicProcedure, router } from "./_core/trpc";

const apiUrl = () => process.env.MODELGUARD_API_URL?.replace(/\/$/, "");

async function callModelGuard(path: string, options?: RequestInit) {
  const origin = apiUrl();
  if (!origin) throw new Error("MODELGUARD_API_URL is not configured.");
  const response = await fetch(`${origin}${path}`, {
    ...options,
    headers: { "content-type": "application/json", ...(options?.headers ?? {}) },
  });
  const payload = await response.json().catch(() => ({ detail: "ModelGuard API returned an invalid response." }));
  if (!response.ok) throw new Error(payload.detail ?? "ModelGuard API request failed.");
  return payload;
}

export const modelGuardRouter = router({
  status: publicProcedure.query(async () => {
    const origin = apiUrl();
    if (!origin) return { connected: false, message: "Preview data is active. Set MODELGUARD_API_URL to connect the FastAPI service." };
    try {
      const health = await callModelGuard("/health");
      return { connected: health.status === "ok", apiUrl: origin, message: "Connected to the persisted ModelGuard API." };
    } catch (error) {
      return { connected: false, message: error instanceof Error ? error.message : "The ModelGuard API is unavailable." };
    }
  }),
  configurations: publicProcedure.query(() => callModelGuard("/configurations")),
  reports: publicProcedure.query(() => callModelGuard("/reports")),
  createConfiguration: publicProcedure.input(z.record(z.string(), z.unknown())).mutation(({ input }) => callModelGuard("/configurations", { method: "POST", body: JSON.stringify(input) })),
  run: publicProcedure.input(z.object({ configurationId: z.string(), payload: z.record(z.string(), z.unknown()).optional() })).mutation(({ input }) => callModelGuard(`/configurations/${input.configurationId}/runs`, { method: "POST", body: JSON.stringify(input.payload ?? {}) })),
  compare: publicProcedure.input(z.object({ leftReportId: z.string(), rightReportId: z.string() })).query(({ input }) => callModelGuard(`/reports/compare/${input.leftReportId}/${input.rightReportId}`)),
});
