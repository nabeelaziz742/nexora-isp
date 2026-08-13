import { BrainCircuit, Clock3 } from "lucide-react";

import type { CopilotActivityItem } from "@/types/intelligence";

interface CopilotActivityProps {
  activities: CopilotActivityItem[];
}

export default function CopilotActivity({
  activities,
}: CopilotActivityProps) {
  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">
          Recent Copilot Activity
        </h2>

        <p className="mt-1 text-xs text-slate-500">
          Recent operational questions and intelligence summaries
        </p>
      </div>

      <div className="divide-y divide-[#202938]">
        {activities.map((activity) => (
          <div key={activity.id} className="px-5 py-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center bg-violet-500/10">
                <BrainCircuit className="h-3.5 w-3.5 text-violet-400" />
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-slate-200">
                  “{activity.query}”
                </p>

                <p className="mt-2 text-[11px] leading-5 text-slate-500">
                  {activity.summary}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
                  <span>{activity.requestedBy}</span>

                  <span>·</span>

                  <span className="flex items-center gap-1">
                    <Clock3 className="h-3 w-3" />
                    {activity.createdAt}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}