import { describe, expect, it } from "vitest";
import { demoFindings, findingsFromReport, metricWidth, summarizeFindings } from "./modelguard";

describe("ModelGuard dashboard helpers", () => {
  it("summarizes pass and fail findings for the dashboard", () => {
    expect(summarizeFindings(demoFindings)).toEqual({ total: 4, passed: 3, failed: 1, health: 75 });
  });

  it("caps evidence meters at 100 percent", () => {
    expect(metricWidth(demoFindings[3])).toBe(100);
  });

  it("converts structured FastAPI results into dashboard findings", () => {
    const findings = findingsFromReport({ results: [{ test_id: "test-1", test_name: "Stable color", kind: "input_perturbation", status: "passed", metric_name: "mean_prediction_delta", metric_value: 0.002, threshold: 0.03, evidence: { feature: "color_code" } }] });
    expect(findings).toMatchObject([{ id: "test-1", kind: "INPUT PERTURBATION", status: "passed", evidence: "feature: color_code" }]);
  });
});
