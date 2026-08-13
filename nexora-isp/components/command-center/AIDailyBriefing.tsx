"use client";

import { FormEvent, useState } from "react";
import {
  BrainCircuit,
  LoaderCircle,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { commandCenterService } from "@/services/command-center-service";

const suggestedQuestions = [
  "What requires my attention right now?",
  "What are the highest operational risks?",
  "Are there collection or provisioning issues?",
];

export default function AIDailyBriefing() {
  const [question, setQuestion] = useState(
    "What requires my attention right now?",
  );
  const [answer, setAnswer] = useState<string | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function askCopilot(
    event?: FormEvent<HTMLFormElement>,
  ) {
    event?.preventDefault();

    const normalizedQuestion = question.trim();

    if (!normalizedQuestion || loading) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setAnswer(null);
      setProvider(null);
      setModel(null);

      const response =
        await commandCenterService.askCopilot(
          normalizedQuestion,
        );

      setAnswer(response.answer);
      setProvider(response.provider);
      setModel(response.model);
    } catch (caughtError) {
      console.error(
        "Failed to ask AI Operations Copilot:",
        caughtError,
      );

      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to generate operational analysis.",
      );
    } finally {
      setLoading(false);
    }
  }

  function useSuggestedQuestion(
    suggestedQuestion: string,
  ) {
    if (loading) {
      return;
    }

    setQuestion(suggestedQuestion);
    setError(null);
  }

  return (
    <section className="border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-md border border-violet-500/20 bg-violet-500/10">
            <BrainCircuit className="size-4 text-violet-400" />
          </div>

          <div>
            <h3 className="text-sm font-semibold text-white">
              AI Operations Copilot
            </h3>

            <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
              Grounded analysis from tenant-scoped ISP operations
            </p>
          </div>
        </div>

        <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-violet-400">
          Read Only
        </span>
      </div>

      <div className="p-5">
        <div className="flex items-start gap-3 border border-blue-500/15 bg-blue-500/[0.06] px-4 py-3">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-blue-400" />

          <p className="text-[10px] leading-5 text-[var(--text-secondary)]">
            Copilot analyzes current operational data only. It
            cannot suspend services, record payments, provision
            accounts, resolve incidents, or change ISP records.
          </p>
        </div>

        <form className="mt-4" onSubmit={askCopilot}>
          <label
            htmlFor="operations-copilot-question"
            className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]"
          >
            Ask about ISP operations
          </label>

          <div className="mt-2 flex gap-2">
            <input
              id="operations-copilot-question"
              type="text"
              value={question}
              disabled={loading}
              maxLength={2000}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              placeholder="What requires my attention right now?"
              className="min-w-0 flex-1 border border-[var(--border)] bg-black/20 px-3.5 py-2.5 text-[12px] text-white outline-none transition placeholder:text-[var(--text-muted)] focus:border-violet-500/50 disabled:cursor-not-allowed disabled:opacity-60"
            />

            <button
              type="submit"
              disabled={!question.trim() || loading}
              className="flex shrink-0 items-center justify-center gap-2 border border-violet-500/30 bg-violet-500/10 px-4 py-2.5 text-[11px] font-semibold text-violet-300 transition hover:bg-violet-500/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}

              <span className="hidden sm:inline">
                {loading ? "Analyzing" : "Ask Copilot"}
              </span>
            </button>
          </div>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {suggestedQuestions.map((suggestedQuestion) => (
            <button
              key={suggestedQuestion}
              type="button"
              disabled={loading}
              onClick={() =>
                useSuggestedQuestion(suggestedQuestion)
              }
              className="border border-[var(--border)] bg-white/[0.02] px-2.5 py-1.5 text-left text-[9px] text-[var(--text-secondary)] transition hover:border-violet-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {suggestedQuestion}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="mt-5 border border-violet-500/15 bg-violet-500/[0.04] px-4 py-5">
            <div className="flex items-center gap-3">
              <LoaderCircle className="size-4 animate-spin text-violet-400" />

              <div>
                <p className="text-[11px] font-medium text-white">
                  Analyzing operational snapshot
                </p>

                <p className="mt-1 text-[10px] text-[var(--text-muted)]">
                  Reviewing tenant-scoped Command Center data.
                </p>
              </div>
            </div>
          </div>
        ) : error ? (
          <div className="mt-5 border border-red-500/20 bg-red-500/[0.06] px-4 py-4">
            <p className="text-[11px] font-medium text-red-400">
              Copilot analysis unavailable
            </p>

            <p className="mt-1.5 text-[10px] leading-5 text-[var(--text-secondary)]">
              {error}
            </p>
          </div>
        ) : answer ? (
          <div className="mt-5 border border-violet-500/15 bg-violet-500/[0.04]">
            <div className="flex items-center justify-between border-b border-violet-500/10 px-4 py-3">
              <div className="flex items-center gap-2">
                <Sparkles className="size-3.5 text-violet-400" />

                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-violet-300">
                  Operational Analysis
                </p>
              </div>

              {provider ? (
                <p className="text-[9px] uppercase tracking-[0.1em] text-[var(--text-muted)]">
                  {provider}
                  {model ? ` · ${model}` : ""}
                </p>
              ) : null}
            </div>

            <div className="px-4 py-4">
              <p className="whitespace-pre-wrap text-[11px] leading-6 text-[var(--text-secondary)]">
                {answer}
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-5 border border-dashed border-[var(--border)] px-4 py-7 text-center">
            <BrainCircuit className="mx-auto size-5 text-violet-400" />

            <p className="mt-3 text-[11px] font-medium text-white">
              Ask the Operations Copilot
            </p>

            <p className="mx-auto mt-1 max-w-md text-[10px] leading-5 text-[var(--text-muted)]">
              Request grounded, read-only analysis of current
              operational risks, collections, provisioning,
              incidents, support work, and communications.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
