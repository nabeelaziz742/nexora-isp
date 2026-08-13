"use client";

import { useEffect, useState } from "react";

import {
  communicationsService,
  type BroadcastOptions,
  type BroadcastChannel,
  type BroadcastAudienceFilter,
} from "@/services/communications.service";

import {
  CalendarClock,
  MessageCircle,
  Mail,
  Send,
  Smartphone,
  Users,
} from "lucide-react";

export default function BroadcastPage() {
  const [options, setOptions] = useState<BroadcastOptions | null>(null);

  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [audience, setAudience] = useState("");
  const [selectedProvider, setSelectedProvider] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [scheduleAt, setScheduleAt] = useState("");

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => {
    loadOptions();
  }, []);

  async function loadOptions() {
    try {
      const data = await communicationsService.getBroadcastOptions();

      setOptions(data);

      if (data.providers.length > 0) {
        setSelectedProvider(data.providers[0].id);
      }

      if (data.audience.length > 0) {
        setAudience(data.audience[0].value);
      }

      if (data.templates.length > 0) {
        setSelectedTemplate(data.templates[0].id);
      }
    } finally {
      setLoading(false);
    }
  }

  function validate(): string | null {
    if (!title.trim()) return "Title is required.";
    if (!message.trim()) return "Message is required.";
    if (!selectedProvider) return "Select a delivery provider.";
    if (!audience) return "Select an audience.";
    return null;
  }

  async function handleSend(scheduled: boolean) {
    const validationError = validate();
    if (validationError) {
      setSendError(validationError);
      return;
    }

    if (scheduled && !scheduleAt) {
      setSendError("Choose a delivery time to schedule.");
      return;
    }

    setSending(true);
    setSendError(null);

    try {
      await communicationsService.createBroadcast({
        provider_id: selectedProvider,
        template_id: selectedTemplate,
        audience,
        title,
        message,
        schedule_at: scheduled ? scheduleAt : null,
      });

      alert("Broadcast queued successfully.");

      setTitle("");
      setMessage("");
      setAudience("");
      setSelectedProvider("");
      setSelectedTemplate("");
      setScheduleAt("");
    } catch (err) {
      setSendError(
        err instanceof Error ? err.message : "Failed to send broadcast."
      );
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-white">
        Loading...
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Broadcast Center
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Send announcements, reminders and campaigns to customers.
          </p>
        </div>

        <button
          onClick={() => handleSend(false)}
          disabled={sending}
          className="flex items-center gap-2 bg-green-500 px-5 py-2 text-sm font-medium text-black hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          {sending ? "Sending..." : "Send Broadcast"}
        </button>
      </div>

      {sendError && (
        <div className="border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-400">
          {sendError}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_420px]">
        <div className="space-y-6">
          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="border-b border-[#202938] px-5 py-4">
              <h2 className="font-semibold text-white">Audience</h2>
            </div>

            <div className="grid gap-4 p-5 md:grid-cols-2">
              {options?.audience?.map((item: BroadcastAudienceFilter) => (
                <button
                  key={item.value}
                  onClick={() => setAudience(item.value)}
                  className={`flex items-center gap-3 border bg-[#080B10] p-4 text-left transition hover:border-blue-500 ${
                    audience === item.value
                      ? "border-blue-500"
                      : "border-[#202938]"
                  }`}
                >
                  <Users className="h-5 w-5 text-cyan-400" />
                  <span className="text-sm text-white">{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="border-b border-[#202938] px-5 py-4">
              <h2 className="font-semibold text-white">Message</h2>
            </div>

            <div className="space-y-4 p-5">
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Broadcast Title"
                className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
              />

              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={10}
                placeholder="Write your broadcast message..."
                className="w-full resize-none border border-[#202938] bg-[#080B10] p-4 text-white outline-none"
              />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="border-b border-[#202938] px-5 py-4">
              <h2 className="font-semibold text-white">Delivery Provider</h2>
            </div>

            <div className="space-y-3 p-5">
              {options?.providers?.map((provider: BroadcastChannel) => {
                const Icon =
                  provider.provider_type === "WHATSAPP"
                    ? MessageCircle
                    : provider.provider_type === "SMS"
                    ? Smartphone
                    : Mail;

                const color =
                  provider.provider_type === "WHATSAPP"
                    ? "text-green-400"
                    : provider.provider_type === "SMS"
                    ? "text-amber-400"
                    : "text-blue-400";

                return (
                  <button
                    key={provider.id}
                    disabled={!provider.is_connected}
                    onClick={() => setSelectedProvider(provider.id)}
                    className={`flex w-full items-center justify-between border bg-[#080B10] p-4 transition hover:border-blue-500 disabled:cursor-not-allowed disabled:opacity-40 ${
                      selectedProvider === provider.id
                        ? "border-blue-500"
                        : "border-[#202938]"
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#111827]">
                        <Icon className={`h-5 w-5 ${color}`} />
                      </div>

                      <span className="text-sm text-white">
                        {provider.name}
                      </span>
                    </div>

                    <span
                      className={`text-xs font-medium ${
                        provider.is_connected
                          ? "text-green-400"
                          : "text-[#64748B]"
                      }`}
                    >
                      {provider.is_connected ? "Connected" : "Not Connected"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="border-b border-[#202938] px-5 py-4">
              <h2 className="font-semibold text-white">Schedule</h2>
            </div>

            <div className="space-y-4 p-5">
              <div>
                <label className="mb-2 block text-xs uppercase tracking-[0.15em] text-[#64748B]">
                  Delivery Time
                </label>

                <input
                  type="datetime-local"
                  value={scheduleAt}
                  onChange={(e) => setScheduleAt(e.target.value)}
                  className="w-full border border-[#202938] bg-[#080B10] px-4 py-3 text-white outline-none"
                />
              </div>

              <button
                onClick={() => handleSend(true)}
                disabled={sending}
                className="flex w-full items-center justify-center gap-2 border border-[#202938] bg-[#080B10] py-3 text-white transition hover:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <CalendarClock className="h-4 w-4" />
                {sending ? "Scheduling..." : "Schedule Broadcast"}
              </button>
            </div>
          </div>

          <div className="border border-[#202938] bg-[#0D1117]">
            <div className="border-b border-[#202938] px-5 py-4">
              <h2 className="font-semibold text-white">Live Preview</h2>
            </div>

            <div className="space-y-4 p-5">
              <div className="rounded-lg border border-[#202938] bg-[#080B10] p-4">
                <p className="whitespace-pre-wrap text-sm leading-7 text-[#CBD5E1]">
                  {message || "Write your broadcast message to preview it here..."}
                </p>
              </div>

              <button
                onClick={() => handleSend(false)}
                disabled={sending}
                className="flex w-full items-center justify-center gap-2 bg-green-500 py-3 font-medium text-black transition hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                {sending ? "Sending..." : "Send Now"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
