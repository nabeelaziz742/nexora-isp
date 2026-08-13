import CopilotActivity from "@/components/intelligence/CopilotActivity";
import CopilotPrompt from "@/components/intelligence/CopilotPrompt";
import OperationalInsights from "@/components/intelligence/OperationalInsights";

import {
  copilotActivity,
  copilotSuggestedPrompts,
  operationalInsights,
} from "@/data/mock/intelligence";

export default function IntelligencePage() {
  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-violet-400">
          ISP Intelligence
        </p>

        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">
          AI ISP Copilot
        </h1>

        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Cross-module operational intelligence for network risk,
          billing exposure, customer behavior, support patterns and
          field operations.
        </p>
      </section>

      <CopilotPrompt prompts={copilotSuggestedPrompts} />

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.7fr)_minmax(340px,0.7fr)]">
        <OperationalInsights insights={operationalInsights} />

        <CopilotActivity activities={copilotActivity} />
      </div>
    </div>
  );
}