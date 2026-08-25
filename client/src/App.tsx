import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import { ComparePage, ReportsPage, RunSuitePage } from "./pages/WorkspaceViews";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/runs" component={RunSuitePage} />
      <Route path="/reports" component={ReportsPage} />
      <Route path="/compare" component={ComparePage} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return <ErrorBoundary><ThemeProvider defaultTheme="light"><TooltipProvider><Toaster richColors position="top-right" /><Router /></TooltipProvider></ThemeProvider></ErrorBoundary>;
}

export default App;
