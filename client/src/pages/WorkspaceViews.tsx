import DashboardLayout from "@/components/DashboardLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { trpc } from "@/lib/trpc";
import { Check, Copy, GitCompareArrows, Play, RefreshCw, ScrollText, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

type Configuration = {
  id: string;
  name: string;
  model_name: string;
  tests: Array<unknown>;
  adapter_type: string;
};

type Report = {
  id: string;
  share_token: string;
  status: "passed" | "failed";
  summary: { total: number; passed: number; failed: number };
  created_at: string;
  report: { model_name?: string };
};

const previewConfigurations: Configuration[] = [
  { id: "preview-eligibility", name: "Eligibility stability", model_name: "credit-risk-v3", adapter_type: "sklearn", tests: [{}, {}, {}, {}] },
  { id: "preview-consistency", name: "Applicant consistency", model_name: "credit-risk-v3", adapter_type: "pytorch", tests: [{}, {}, {}] },
];

const previewReports: Report[] = [
  { id: "preview-report-current", share_token: "demo-current", status: "failed", summary: { total: 4, passed: 3, failed: 1 }, created_at: "2026-08-25T10:40:00.000Z", report: { model_name: "credit-risk-v3.2" } },
  { id: "preview-report-baseline", share_token: "demo-baseline", status: "passed", summary: { total: 4, passed: 4, failed: 0 }, created_at: "2026-08-18T10:40:00.000Z", report: { model_name: "credit-risk-v3.1" } },
];

const previewComparisonRows = [
  { test_id: "stability", test_name: "Irrelevant color-code stability", left_status: "passed", right_status: "passed", metric_delta: 0.002 },
  { test_id: "boundary", test_name: "Income boundary resilience", left_status: "passed", right_status: "passed", metric_delta: 0.011 },
  { test_id: "shift", test_name: "Application input shift", left_status: "passed", right_status: "failed", metric_delta: 0.041 },
];

function ApiState({ children }: { children: React.ReactNode }) {
  const status = trpc.modelguard.status.useQuery();
  const live = status.data?.connected === true;
  return (
    <>
      {!live && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#e8ddfc] px-4 py-3 text-[#4d4263] shadow-[2px_3px_0_rgba(75,62,99,0.12)]">
          <p className="text-xs font-bold">Preview mode is active. These controls use bundled sample evidence until the FastAPI service is connected.</p>
          <span className="rounded-full bg-[#f9f4ff] px-2.5 py-1 text-[10px] font-black tracking-[0.12em]">SAFE SANDBOX</span>
        </div>
      )}
      {children}
    </>
  );
}

function QueryError({ error, label }: { error: { message: string }; label: string }) {
  return <div className="cutout-card bg-[#ffe1d9] p-5 text-[#8c3f34]"><p className="font-display text-xl font-black tracking-[-0.05em]">Could not load {label}.</p><p className="mt-2 text-sm leading-relaxed">{error.message}</p></div>;
}

function Shell({ eyebrow, title, children }: { eyebrow: string; title: React.ReactNode; children: React.ReactNode }) {
  return <DashboardLayout><div className="mx-auto max-w-5xl pb-10"><p className="label text-[#08706d]">{eyebrow}</p><h1 className="mt-2 font-display text-4xl font-black tracking-[-0.075em] text-[#163d3e] sm:text-5xl">{title}</h1><div className="mt-8">{children}</div></div></DashboardLayout>;
}

export function RunSuitePage() {
  const utils = trpc.useUtils();
  const status = trpc.modelguard.status.useQuery();
  const live = status.data?.connected === true;
  const configurations = trpc.modelguard.configurations.useQuery(undefined, { enabled: live });
  const run = trpc.modelguard.run.useMutation({
    onSuccess: () => { void utils.modelguard.reports.invalidate(); toast.success("Test run finished and was persisted."); },
    onError: error => toast.error("Test run failed", { description: error.message }),
  });
  const items = live ? (configurations.data ?? []) as Configuration[] : previewConfigurations;

  if (live && configurations.isError) return <Shell eyebrow="Launch a suite" title={<>Make a promise.<br /><span className="text-[#f06c58]">Then prove it.</span></>}><ApiState><QueryError label="test configurations" error={configurations.error} /></ApiState></Shell>;
  const launch = (configurationId: string) => {
    if (live) run.mutate({ configurationId });
    else toast.success("Preview suite completed", { description: "4 behavior checks were evaluated against the bundled credit-risk-v3 report." });
  };

  return <Shell eyebrow="Launch a suite" title={<>Make a promise.<br /><span className="text-[#f06c58]">Then prove it.</span></>}><ApiState><div className="grid gap-4 md:grid-cols-2">{items.map(config => <article key={config.id} className="cutout-card bg-[#fffdf7] p-6"><div className="flex items-start justify-between gap-3"><div><p className="label">{config.adapter_type} adapter</p><h2 className="mt-2 font-display text-2xl font-black tracking-[-0.055em] text-[#27413a]">{config.name}</h2><p className="mt-2 text-sm text-[#6f7c75]">{config.model_name} · {config.tests.length} authored checks</p></div><Badge className="rounded-full border-0 bg-[#d9f0e8] text-[#07635f]">READY</Badge></div><Button onClick={() => launch(config.id)} disabled={run.isPending} className="mt-6 h-10 rounded-2xl bg-[#075f63] font-extrabold text-white shadow-[3px_4px_0_#f29a86]"><Play className="mr-2 h-4 w-4 fill-current" />{run.isPending ? "Running…" : "Run this suite"}</Button></article>)}</div></ApiState></Shell>;
}

export function ReportsPage() {
  const status = trpc.modelguard.status.useQuery();
  const live = status.data?.connected === true;
  const reports = trpc.modelguard.reports.useQuery(undefined, { enabled: live });
  const items = live ? (reports.data ?? []) as Report[] : previewReports;
  const share = async (report: Report) => {
    const apiUrl = status.data && "apiUrl" in status.data ? status.data.apiUrl : undefined;
    await navigator.clipboard?.writeText(apiUrl ? `${apiUrl}/reports/share/${report.share_token}` : `https://modelguard.local/reports/${report.share_token}`);
    toast.success("Share link copied", { description: live ? "The persisted report URL is ready to send." : "Preview report URL copied." });
  };

  if (live && reports.isError) return <Shell eyebrow="Test reports" title={<>Evidence that<br /><span className="text-[#0a7775]">travels with the model.</span></>}><ApiState><QueryError label="persisted reports" error={reports.error} /></ApiState></Shell>;
  return <Shell eyebrow="Test reports" title={<>Evidence that<br /><span className="text-[#0a7775]">travels with the model.</span></>}><ApiState><div className="space-y-4">{items.map(report => <article key={report.id} className="cutout-card flex flex-col gap-4 bg-[#fffdf7] p-5 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-4"><span className={`grid h-11 w-11 place-items-center rounded-2xl ${report.status === "passed" ? "bg-[#d9f0e8] text-[#07635f]" : "bg-[#ffe0d8] text-[#a63f32]"}`}>{report.status === "passed" ? <Check className="h-5 w-5" strokeWidth={3} /> : <TriangleAlert className="h-5 w-5" />}</span><div><p className="font-display text-xl font-black tracking-[-0.05em] text-[#27413a]">{report.report.model_name ?? "ModelGuard report"}</p><p className="mt-1 text-xs font-bold text-[#728079]">{new Date(report.created_at).toLocaleString()} · {report.summary.passed}/{report.summary.total} checks passed</p></div></div><Button onClick={() => void share(report)} variant="outline" className="h-9 rounded-xl border-0 bg-[#fff1d0] font-extrabold text-[#6a521a] shadow-[2px_3px_0_rgba(90,66,23,0.12)]"><Copy className="mr-2 h-3.5 w-3.5" />Share report</Button></article>)}</div></ApiState></Shell>;
}

export function ComparePage() {
  const status = trpc.modelguard.status.useQuery();
  const live = status.data?.connected === true;
  const reports = trpc.modelguard.reports.useQuery(undefined, { enabled: live });
  const items = live ? (reports.data ?? []) as Report[] : previewReports;
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  useEffect(() => { if (items.length > 1 && (!left || !right)) { setLeft(items[1].id); setRight(items[0].id); } }, [items, left, right]);
  const comparison = trpc.modelguard.compare.useQuery({ leftReportId: left, rightReportId: right }, { enabled: live && Boolean(left) && Boolean(right) && left !== right });

  if (live && (reports.isError || comparison.isError)) return <Shell eyebrow="Compare reports" title={<>See release drift<br /><span className="text-[#b54c3e]">before it ships.</span></>}><ApiState><QueryError label="comparison data" error={reports.error ?? comparison.error!} /></ApiState></Shell>;
  const rows = (live ? comparison.data?.comparisons ?? [] : previewComparisonRows) as Array<{ test_id: string; test_name: string; left_status: string; right_status: string; metric_delta: number }>;

  return <Shell eyebrow="Compare reports" title={<>See release drift<br /><span className="text-[#b54c3e]">before it ships.</span></>}><ApiState><div className="cutout-card bg-[#fffdf7] p-6"><div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center"><select value={left} onChange={event => setLeft(event.target.value)} className="h-11 rounded-2xl border-0 bg-[#fff1d0] px-3 text-sm font-bold text-[#5f4918]">{items.map(item => <option key={item.id} value={item.id}>{item.report.model_name} · {new Date(item.created_at).toLocaleDateString()}</option>)}</select><GitCompareArrows className="mx-auto h-6 w-6 text-[#0a7775]" /><select value={right} onChange={event => setRight(event.target.value)} className="h-11 rounded-2xl border-0 bg-[#d9f0e8] px-3 text-sm font-bold text-[#075f63]">{items.map(item => <option key={item.id} value={item.id}>{item.report.model_name} · {new Date(item.created_at).toLocaleDateString()}</option>)}</select></div><div className="mt-7 space-y-2">{live && comparison.isLoading ? <p className="flex items-center text-sm font-bold text-[#647069]"><RefreshCw className="mr-2 h-4 w-4 animate-spin" />Comparing evidence…</p> : rows.map(item => <div key={item.test_id} className="flex items-center justify-between rounded-2xl bg-[#f6f1e8] px-4 py-3"><span className="text-sm font-extrabold text-[#30443c]">{item.test_name}</span><span className="text-xs font-black text-[#647069]">{item.left_status} → {item.right_status} · Δ {item.metric_delta.toFixed(3)}</span></div>)}</div></div></ApiState></Shell>;
}
