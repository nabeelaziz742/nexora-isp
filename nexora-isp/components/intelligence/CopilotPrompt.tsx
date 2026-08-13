"use client";

import { useState } from "react";
import {
  ArrowUp,
  BadgeDollarSign,
  BrainCircuit,
  CircleAlert,
  Command,
  Network,
  RadioTower,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";

import type {
  CopilotPromptIcon,
  CopilotSuggestedPrompt,
} from "@/types/intelligence";

interface CopilotPromptProps {
  prompts: CopilotSuggestedPrompt[];
}

const promptIcons = {
  RADIO_TOWER: RadioTower,
  BADGE_DOLLAR: BadgeDollarSign,
  USERS: Users,
  CIRCLE_ALERT: CircleAlert,
  NETWORK: Network,
  TRENDING_UP: TrendingUp,
} satisfies Record<CopilotPromptIcon, typeof RadioTower>;

export default function CopilotPrompt({
  prompts,
}: CopilotPromptProps) {
  const [query, setQuery] = useState("");

  function handleSuggestedPrompt(prompt: string) {
    setQuery(prompt);
  }

  function handleSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!query.trim()) {
      return;
    }

    /*
     * Frontend checkpoint only.
     *
     * Later:
     * UI
     * ↓
     * Copilot API Service
     * ↓
     * Django Intelligence Endpoint
     * ↓
     * Operational Context Retrieval
     * ↓
     * AI Engine
     */
  }

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="border-b border-[#202938] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-violet-500/10">
            <BrainCircuit className="h-5 w-5 text-violet-400" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-100">
                NEXORA AI Copilot
              </h2>

              <span className="bg-violet-500/10 px-2 py-1 text-[10px] font-semibold text-violet-400">
                INTELLIGENCE
              </span>
            </div>

            <p className="mt-1 text-xs text-slate-500">
              Operational intelligence across your ISP command
              environment
            </p>
          </div>
        </div>
      </div>

      <div className="px-5 py-6">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-400" />

            <p className="text-xs font-medium uppercase tracking-[0.1em] text-violet-400">
              Ask NEXORA
            </p>
          </div>

          <h3 className="mt-3 text-xl font-semibold tracking-tight text-slate-50">
            What do you want to understand about your ISP?
          </h3>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Analyze network conditions, billing exposure, customer
            behavior, support patterns and field operations.
          </p>

          <form
            onSubmit={handleSubmit}
            className="mt-6 border border-[#2B3545] bg-[#070A0F]"
          >
            <textarea
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              placeholder="Ask about network risk, revenue exposure, customer churn, incidents..."
              rows={4}
              className="w-full resize-none bg-transparent px-4 py-4 text-sm leading-6 text-slate-200 outline-none placeholder:text-slate-600"
            />

            <div className="flex items-center justify-between border-t border-[#202938] px-3 py-3">
              <div className="flex items-center gap-2 text-[11px] text-slate-600">
                <Command className="h-3.5 w-3.5" />
                Operational context aware
              </div>

              <button
                type="submit"
                disabled={!query.trim()}
                className="flex h-9 items-center gap-2 bg-violet-600 px-4 text-xs font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Analyze ISP
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            </div>
          </form>

          <div className="mt-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-600">
              Suggested Operational Queries
            </p>

            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {prompts.map((prompt) => {
                const Icon = promptIcons[prompt.icon];

                return (
                  <button
                    key={prompt.id}
                    type="button"
                    onClick={() =>
                      handleSuggestedPrompt(prompt.prompt)
                    }
                    className="group border border-[#202938] bg-[#121821] p-3 text-left transition hover:border-violet-500/40 hover:bg-violet-500/5"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="h-3.5 w-3.5 text-slate-500 transition group-hover:text-violet-400" />

                      <span className="text-xs font-medium text-slate-300">
                        {prompt.title}
                      </span>
                    </div>

                    <p className="mt-2 text-[11px] leading-5 text-slate-600">
                      {prompt.prompt}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}