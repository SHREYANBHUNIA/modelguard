import DashboardLayout from "@/components/DashboardLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { demoFindings, findingsFromReport, metricWidth, summarizeFindings, testCatalog, type BehaviorFinding } from "@/lib/modelguard";
import { trpc } from "@/lib/trpc";
import {
  ArrowRight,
  Check,
  CircleDotDashed,
  Clock3,
  Copy,
  ExternalLink,
  FlaskConical,
  GitCompareArrows,
  Play,
  Radar,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

const statusClass: Record<BehaviorFinding["status"], string> = {
  passed: "bg-[#d9f0e8] text-[#07635f]",
  failed: "bg-[#ffe0d8] text-[#a63f32]",
};

function FindingRow({ finding, onSelect, selected }: { finding: BehaviorFinding; onSelect: (item: BehaviorFinding) => void; selected: boolean }) {
  return (
    <button onClick={() => onSelect(finding)} className={`group grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl px-3 py-3 text-left transition-all hover:-translate-y-0.5 hover:bg-[#fff7e8] ${selected ? "bg-[#fff1d0] shadow-[2px_3px_0_rgba(68,74,70,0.12)]" : ""}`}>
      <span className={`grid h-8 w-8 place-items-center rounded-xl ${statusClass[finding.status]}`}>
        {finding.status === "passed" ? <Check className="h-4 w-4" strokeWidth={3} /> : <TriangleAlert className="h-4 w-4" strokeWidth={2.7} />}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-extrabold text-[#26352f]">{finding.name}</span>
        <span className="mt-0.5 block text-[10px] font-bold tracking-[0.08em] text-[#838b85]">{finding.kind}</span>
      </span>
      <ArrowRight className="h-4 w-4 text-[#93a097] transition-transform group-hover:translate-x-0.5" />
    </button>
  );
}

export default function Home() {
  const [selected, setSelected] = useState(demoFindings[0]);
  const [runState, setRunState] = useState<"idle" | "running" | "done">("idle");
  const utils = trpc.useUtils();
  const connection = trpc.modelguard.status.useQuery();
  const configurations = trpc.modelguard.configurations.useQuery(undefined, { enabled: connection.data?.connected === true });
  const reports = trpc.modelguard.reports.useQuery(undefined, { enabled: connection.data?.connected === true });
  const persistedReports = (reports.data ?? []) as Array<{ id: string; share_token: string; report: unknown }>;
  const latestReport = persistedReports[0];
  const findings = latestReport ? findingsFromReport(latestReport.report) : demoFindings;
  const summary = summarizeFindings(findings);
  const runMutation = trpc.modelguard.run.useMutation({
    onSuccess: () => {
      setRunState("done");
      void utils.modelguard.reports.invalidate();
      toast.success("Suite completed", { description: "The persisted FastAPI report is ready to inspect and share." });
    },
    onError: error => {
      setRunState("idle");
      toast.error("Suite could not run", { description: error.message });
    },
  });
  const comparison = trpc.modelguard.compare.useQuery(
    { leftReportId: persistedReports[0]?.id ?? "", rightReportId: persistedReports[1]?.id ?? "" },
    { enabled: connection.data?.connected === true && persistedReports.length > 1 },
  );

  useEffect(() => {
    if (!findings.some(item => item.id === selected.id)) setSelected(findings[0] ?? demoFindings[0]);
  }, [findings, selected.id]);

  const runSuite = () => {
    const configuration = (configurations.data ?? []) as Array<{ id: string }>;
    if (connection.data?.connected) {
      if (!configuration[0]) {
        toast.error("No persisted suite found", { description: "Create a configuration through the ModelGuard API before launching a run." });
        return;
      }
      setRunState("running");
      runMutation.mutate({ configurationId: configuration[0].id });
      return;
    }
    setRunState("running");
    window.setTimeout(() => {
      setRunState("done");
      toast.success("Suite completed", { description: "4 checks were evaluated against credit-risk-v3." });
    }, 650);
  };

  const shareReport = async () => {
    const apiUrl = connection.data && "apiUrl" in connection.data ? connection.data.apiUrl : undefined;
    const url = latestReport && apiUrl ? `${apiUrl}/reports/share/${latestReport.share_token}` : "https://modelguard.local/reports/demo-042";
    await navigator.clipboard?.writeText(url);
    toast.success("Share link copied", { description: latestReport ? "Anyone with the link can inspect the persisted report." : "Preview share link copied." });
  };

  return (
    <DashboardLayout>
      <div className="relative mx-auto max-w-[1440px] overflow-hidden pb-10">
        <span className="paper-shape paper-circle absolute right-[13%] top-6 h-10 w-10 bg-[#f5c54d]" />
        <span className="paper-shape paper-circle absolute right-0 top-28 h-20 w-20 bg-[#f29a86]" />
        <span className="paper-shape paper-triangle absolute left-[42%] top-3 border-b-[30px] border-l-[20px] border-r-[20px] border-b-[#b9a3e8]" />

        <header className="relative mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#ecf5e9] px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-[#21705c]">
              <Sparkles className="h-3.5 w-3.5" /> Reliable ML starts here
            </div>
            <h1 className="font-display text-4xl font-black leading-[0.93] tracking-[-0.075em] text-[#163d3e] sm:text-5xl">Behavior, <span className="text-[#f06c58]">not just</span><br />accuracy.</h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#627069]">Define sharp expectations, turn them into tests, and keep every model release accountable.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" onClick={shareReport} className="h-11 rounded-2xl border-0 bg-[#fffdf7] px-4 font-extrabold text-[#27413a] shadow-[3px_4px_0_rgba(44,59,51,0.13)] hover:bg-[#f3ebe0]">
              <Copy className="mr-2 h-4 w-4" /> Share report
            </Button>
            <Button onClick={runSuite} disabled={runState === "running"} className="h-11 rounded-2xl bg-[#075f63] px-5 font-extrabold text-[#fffaf0] shadow-[4px_5px_0_#f29a86] hover:bg-[#054e52]">
              {runState === "running" ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4 fill-current" />}
              {runState === "running" ? "Testing…" : "Run behavior suite"}
            </Button>
          </div>
        </header>

        <section className="relative grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="cutout-card bg-[#d9f0e8] p-5"><p className="label">Release health</p><div className="mt-4 flex items-end justify-between"><span className="font-display text-5xl font-black tracking-[-0.08em] text-[#055d63]">{summary.health}%</span><ShieldCheck className="h-9 w-9 text-[#07826e]" /></div><p className="mt-3 text-xs font-bold text-[#367366]">{summary.passed} of {summary.total} safeguards cleared</p></div>
          <div className="cutout-card bg-[#fff0cf] p-5"><p className="label">Active suite</p><p className="mt-4 font-display text-xl font-black tracking-[-0.05em] text-[#60471b]">Eligibility<br />stability</p><p className="mt-3 text-xs font-bold text-[#886b2d]">credit-risk-v3 · 4 checks</p></div>
          <div className="cutout-card bg-[#e8ddfc] p-5"><p className="label">Latest baseline</p><p className="mt-4 font-display text-xl font-black tracking-[-0.05em] text-[#483b62]">v3.1<br />approved</p><p className="mt-3 text-xs font-bold text-[#746486]">99.6% prediction agreement</p></div>
          <div className="cutout-card bg-[#ffe1d9] p-5"><p className="label">Needs attention</p><div className="mt-4 flex items-center gap-3"><span className="font-display text-5xl font-black tracking-[-0.08em] text-[#b54c3e]">{summary.failed}</span><TriangleAlert className="h-8 w-8 text-[#c94f3c]" /></div><p className="mt-3 text-xs font-bold text-[#9f5d51]">Shift test crossed its limit</p></div>
        </section>

        <section className="relative mt-7 grid gap-5 xl:grid-cols-[1.35fr_0.9fr]">
          <div className="cutout-card bg-[#fffdf7] p-5 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex items-center gap-2"><span className="relative grid h-9 w-9 place-items-center rounded-xl bg-[#075f63] text-white shadow-[2px_3px_0_#f5c54d]"><FlaskConical className="h-4 w-4" /></span><h2 className="font-display text-2xl font-black tracking-[-0.06em] text-[#243d38]">A run you can explain.</h2></div><p className="mt-2 text-sm text-[#728079]">Every result comes with a test, a threshold, and evidence.</p></div><Badge className="w-fit rounded-full border-0 bg-[#fff0cf] px-3 py-1 text-[10px] font-black tracking-[0.13em] text-[#71551d]">{latestReport ? "LIVE PERSISTED REPORT" : "PREVIEW REPORT · 04:20"}</Badge></div>
            <div className="mt-5 divide-y divide-[#ece6db]">{findings.map(finding => <FindingRow key={finding.id} finding={finding} selected={selected.id === finding.id} onSelect={setSelected} />)}</div>
            <button onClick={() => connection.data?.connected ? void utils.modelguard.reports.invalidate() : toast("Connect the FastAPI service to browse persisted report history.")} className="mt-5 inline-flex items-center text-xs font-black text-[#06636a] hover:underline">Refresh report evidence <ExternalLink className="ml-1.5 h-3.5 w-3.5" /></button>
          </div>

          <aside className="cutout-card bg-[#173f40] p-6 text-[#fff9ed]">
            <div className="flex items-start justify-between"><div><p className="text-[10px] font-black tracking-[0.18em] text-[#a3d5ca]">SELECTED EVIDENCE</p><h2 className="mt-2 font-display text-2xl font-black tracking-[-0.06em]">{selected.name}</h2></div><span className={`rounded-full px-3 py-1 text-[10px] font-black tracking-[0.12em] ${selected.status === "passed" ? "bg-[#aee1cc] text-[#075f63]" : "bg-[#ffc1b4] text-[#9b392b]"}`}>{selected.status.toUpperCase()}</span></div>
            <div className="mt-7 rounded-2xl bg-[#215355] p-4"><p className="text-xs font-bold text-[#c9ebe1]">{selected.metric}</p><div className="mt-2 flex items-baseline gap-2"><span className="font-display text-4xl font-black tracking-[-0.07em]">{selected.value.toFixed(selected.value < 0.1 ? 3 : 2)}</span><span className="text-xs font-bold text-[#a9c8c0]">limit {selected.threshold}</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-[#396567]"><div className={`h-full rounded-full ${selected.status === "passed" ? "bg-[#aee1cc]" : "bg-[#ff9e8b]"}`} style={{ width: `${metricWidth(selected)}%` }} /></div></div>
            <div className="mt-5 flex gap-3 rounded-2xl border border-[#377173] p-4"><Radar className="mt-0.5 h-5 w-5 shrink-0 text-[#f5c54d]" /><div><p className="text-sm font-extrabold">Evidence footprint</p><p className="mt-1 text-xs leading-relaxed text-[#c3ddd6]">{selected.evidence}. Threshold applied exactly as authored in the suite.</p></div></div>
            <Button onClick={() => toast("Evidence packet prepared", { description: "The FastAPI report endpoint exposes this test's full JSON record." })} variant="ghost" className="mt-5 h-9 rounded-xl px-0 text-xs font-black text-[#f5d66d] hover:bg-transparent hover:text-[#fff0af]">Inspect raw evidence <ArrowRight className="ml-1 h-4 w-4" /></Button>
          </aside>
        </section>

        <section className="relative mt-7 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="cutout-card bg-[#f5c54d] p-6 text-[#5a4217]"><div className="flex items-start justify-between"><div><p className="label text-[#795d23]">Compare releases</p><h2 className="mt-2 font-display text-3xl font-black tracking-[-0.065em]">What changed?<br />See it fast.</h2></div><GitCompareArrows className="h-9 w-9" /></div><div className="mt-7 flex flex-wrap items-center gap-3"><span className="rounded-xl bg-[#fff6d4] px-3 py-2 text-xs font-black shadow-[2px_3px_0_rgba(90,66,23,0.16)]">{persistedReports.length > 1 ? "older report" : "v3.1 baseline"}</span><ArrowRight className="h-4 w-4" /><span className="rounded-xl bg-[#075f63] px-3 py-2 text-xs font-black text-white shadow-[2px_3px_0_rgba(90,66,23,0.16)]">{latestReport ? "latest persisted" : "v3.2 candidate"}</span></div><Button onClick={() => comparison.data ? toast("Comparison loaded", { description: `${comparison.data.comparisons.length} test deltas are ready for review.` }) : toast("Need two persisted reports", { description: "Run the suite twice after connecting the FastAPI service to compare releases." })} className="mt-6 h-10 rounded-2xl bg-[#fff9ed] font-extrabold text-[#5a4217] shadow-[3px_4px_0_rgba(90,66,23,0.16)] hover:bg-[#fffef9]">Open comparison <ArrowRight className="ml-2 h-4 w-4" /></Button></div>
          <div className="cutout-card bg-[#e8ddfc] p-6"><p className="label text-[#6a5b82]">Test library</p><div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">{testCatalog.slice(0, 6).map(([name, note]) => <div key={name} className="rounded-2xl bg-[#f9f4ff] px-3 py-2.5 shadow-[1px_2px_0_rgba(75,62,99,0.12)]"><p className="text-xs font-extrabold text-[#514568]">{name}</p><p className="mt-0.5 text-[10px] text-[#807391]">{note}</p></div>)}</div><button onClick={() => toast("All 9 ModelGuard test types are ready in the Python engine.")} className="mt-4 inline-flex items-center text-xs font-black text-[#625275] hover:underline">Explore all 9 test types <ArrowRight className="ml-1 h-3.5 w-3.5" /></button></div>
        </section>

        <div className="relative mt-7 flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-dashed border-[#cfc5b5] bg-[#fffdf7]/70 px-5 py-4"><div className="flex items-center gap-3"><CircleDotDashed className="h-5 w-5 text-[#0b7c76]" /><p className="text-xs font-bold text-[#647069]">{connection.data?.connected ? "Connected to the persisted ModelGuard API. Results refresh after every run." : "Preview data is active. Set MODELGUARD_API_URL to connect the persisted FastAPI service."}</p></div><div className="flex items-center gap-2 text-xs font-extrabold text-[#52635b]"><Clock3 className="h-4 w-4" /> {connection.isLoading ? "Checking connection" : latestReport ? "Latest persisted run" : "Preview run 04:20 ago"}</div></div>
      </div>
    </DashboardLayout>
  );
}
