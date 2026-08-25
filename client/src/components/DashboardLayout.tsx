import { useAuth } from "@/_core/hooks/useAuth";
import {
  Activity,
  Beaker,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  GitCompareArrows,
  LogIn,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useLocation } from "wouter";
import { startLogin } from "@/const";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

const navigation = [
  { icon: Activity, label: "Control room", path: "/" },
  { icon: Beaker, label: "Run a suite", path: "/runs" },
  { icon: ChartNoAxesCombined, label: "Reports", path: "/reports" },
  { icon: GitCompareArrows, label: "Compare", path: "/compare" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [location, setLocation] = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <SidebarProvider defaultOpen>
      <Sidebar className="border-r-0 bg-transparent" collapsible="icon">
        <SidebarHeader className="h-auto px-4 pt-5 pb-5">
          <button onClick={() => setLocation("/")} className="flex items-center gap-3 text-left">
            <span className="relative grid h-11 w-11 place-items-center rounded-[16px] bg-[#055d63] text-[#fff9ed] shadow-[4px_5px_0_#f29a86]">
              <ShieldCheck className="h-6 w-6" strokeWidth={2.6} />
              <i className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-[#f5c54d]" />
            </span>
            <span className="group-data-[collapsible=icon]:hidden">
              <span className="block font-display text-xl font-black tracking-[-0.07em]">ModelGuard</span>
              <span className="block text-[10px] font-bold uppercase tracking-[0.18em] text-[#5f6a64]">Behavior lab</span>
            </span>
          </button>
        </SidebarHeader>

        <SidebarContent className="px-3">
          <p className="px-3 pb-2 text-[10px] font-extrabold uppercase tracking-[0.18em] text-[#77807b] group-data-[collapsible=icon]:hidden">Workspace</p>
          <SidebarMenu>
            {navigation.map(item => {
              const active = location === item.path || (item.path === "/" && location === "");
              return (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton
                    isActive={active}
                    tooltip={item.label}
                    onClick={() => setLocation(item.path)}
                    className="h-11 rounded-2xl px-3 text-[#46514c] transition-all hover:-translate-y-0.5 hover:bg-[#fdf4e4] data-[active=true]:bg-[#d9f0e8] data-[active=true]:font-bold data-[active=true]:text-[#035c61]"
                  >
                    <item.icon className="h-[18px] w-[18px]" strokeWidth={2.25} />
                    <span>{item.label}</span>
                    {active && <ChevronRight className="ml-auto h-4 w-4 group-data-[collapsible=icon]:hidden" />}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>

          <div className="cutout-note mx-2 mt-8 rounded-3xl bg-[#e7ddfb] p-4 text-[#4b3e63] group-data-[collapsible=icon]:hidden">
            <CircleHelp className="mb-3 h-5 w-5" />
            <p className="text-sm font-extrabold">Need a test idea?</p>
            <p className="mt-1 text-xs leading-relaxed opacity-80">Start with an irrelevant feature and prove it stays irrelevant.</p>
          </div>
        </SidebarContent>

        <SidebarFooter className="p-3">
          <div className="rounded-2xl bg-[#fffaf0] p-3 shadow-[2px_3px_0_rgba(68,74,70,0.12)] group-data-[collapsible=icon]:p-1">
            <p className="text-sm font-bold text-[#24342f] group-data-[collapsible=icon]:hidden">{isAuthenticated ? user?.name || "Analyst" : "Preview workspace"}</p>
            <p className="mt-0.5 text-xs text-[#75807a] group-data-[collapsible=icon]:hidden">{isAuthenticated ? user?.email || "Signed in" : "No data leaves your browser"}</p>
            <Button onClick={isAuthenticated ? logout : startLogin} variant="ghost" className="mt-2 h-8 w-full justify-start rounded-xl px-2 text-xs font-bold hover:bg-[#f3ebe0] group-data-[collapsible=icon]:mt-0 group-data-[collapsible=icon]:w-8">
              {isAuthenticated ? <LogOut className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
              <span className="ml-2 group-data-[collapsible=icon]:hidden">{isAuthenticated ? "Sign out" : "Sign in"}</span>
            </Button>
          </div>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset className="min-h-screen bg-[#fff9ed]">
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-[#eee5d8] bg-[#fff9ed]/95 px-4 py-3 backdrop-blur md:hidden">
          <SidebarTrigger className="h-9 w-9 rounded-xl bg-[#d9f0e8] text-[#055d63] shadow-[2px_3px_0_rgba(5,93,99,0.15)]" />
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#055d63]" /><span className="font-display text-sm font-black tracking-[-0.05em] text-[#163d3e]">ModelGuard</span></div>
          <span className="h-2.5 w-2.5 rounded-full bg-[#f5c54d] shadow-[1px_1px_0_#de855f]" />
        </div>
        <main className="min-h-screen px-4 py-4 sm:px-7 sm:py-7 lg:px-9">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
