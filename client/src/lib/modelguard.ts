export type FindingStatus = "passed" | "failed";

export type BehaviorFinding = {
  id: string;
  name: string;
  kind: string;
  status: FindingStatus;
  metric: string;
  value: number;
  threshold: number;
  evidence: string;
};

export const testCatalog = [
  ["Input perturbation", "Hold irrelevant changes steady"],
  ["Boundary cases", "Test edges before users do"],
  ["Distribution shift", "Spot input drift early"],
  ["Feature sensitivity", "Measure what moves outputs"],
  ["Prediction consistency", "Repeat without surprises"],
  ["Outlier resilience", "Probe the strange inputs"],
  ["Data leakage", "Catch suspicious shortcuts"],
  ["Regression baseline", "Protect approved behavior"],
  ["Model comparison", "Compare candidates honestly"],
] as const;

export const demoFindings: BehaviorFinding[] = [
  { id: "stable-color", name: "Irrelevant color-code stability", kind: "INPUT PERTURBATION", status: "passed", metric: "Mean prediction delta", value: 0.002, threshold: 0.03, evidence: "color_code +4.0 · 250 rows" },
  { id: "income-boundary", name: "Income boundary resilience", kind: "BOUNDARY", status: "passed", metric: "Max boundary delta", value: 0.011, threshold: 0.04, evidence: "income at 0, 25k, 250k" },
  { id: "release-regression", name: "Approved-release regression", kind: "REGRESSION", status: "passed", metric: "Baseline agreement", value: 0.996, threshold: 0.99, evidence: "credit-risk-v3.1 baseline" },
  { id: "application-shift", name: "Application input shift", kind: "DISTRIBUTION SHIFT", status: "failed", metric: "Population stability index", value: 0.241, threshold: 0.2, evidence: "employment_length distribution" },
];

export function summarizeFindings(findings: BehaviorFinding[]) {
  const passed = findings.filter(item => item.status === "passed").length;
  return { total: findings.length, passed, failed: findings.length - passed, health: Math.round((passed / findings.length) * 100) };
}

export function metricWidth(finding: BehaviorFinding) {
  const denominator = finding.threshold || 1;
  return Math.min(100, Math.round((finding.value / denominator) * 100));
}

export function findingsFromReport(report: unknown): BehaviorFinding[] {
  if (!report || typeof report !== "object" || !("results" in report) || !Array.isArray(report.results)) return [];
  return report.results.flatMap((result, index) => {
    if (!result || typeof result !== "object") return [];
    const item = result as Record<string, unknown>;
    if (typeof item.test_id !== "string" || typeof item.test_name !== "string" || (item.status !== "passed" && item.status !== "failed")) return [];
    return [{
      id: item.test_id,
      name: item.test_name,
      kind: typeof item.kind === "string" ? item.kind.replaceAll("_", " ").toUpperCase() : "MODEL BEHAVIOR",
      status: item.status,
      metric: typeof item.metric_name === "string" ? item.metric_name.replaceAll("_", " ") : "Behavior metric",
      value: typeof item.metric_value === "number" ? item.metric_value : 0,
      threshold: typeof item.threshold === "number" ? item.threshold : 0,
      evidence: typeof item.evidence === "object" && item.evidence ? Object.entries(item.evidence as Record<string, unknown>).map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`).join(" · ") : `Result ${index + 1}`,
    }];
  });
}
