"use client";

import Link from "next/link";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { communicationsService } from "@/services/communications.service";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Eye,
  Copy,
  Pencil,
  Trash2,
  Plus,
  Search,
  FileText,
  MessageCircle,
  Mail,
  Smartphone,
  Filter,
} from "lucide-react";

export default function CommunicationTemplatesPage() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [stats, setStats] = useState({
    total: 0,
    whatsapp: 0,
    sms: 0,
    email: 0,
  });

  const [previewOpen, setPreviewOpen] =
    useState(false);

  const [previewData, setPreviewData] =
    useState<any>(null);

  useEffect(() => {
    loadTemplates();
  }, [
    search,
    providerFilter,
    statusFilter,
  ]);

  async function loadTemplates() {
    try {
      setLoading(true);

      const response =
        await communicationsService.getTemplates({
          search,
          status:
            statusFilter === "ALL"
              ? undefined
              : statusFilter,
          provider:
            providerFilter === "ALL"
              ? undefined
              : providerFilter,
        });

      const items = Array.isArray(response)
        ? response
        : response.results ?? [];

      setTemplates(items);

      setStats({
        total: items.length,
        whatsapp: items.filter(
          (t: any) =>
            t.communication_provider_type === "WHATSAPP",
        ).length,
        sms: items.filter(
          (t: any) =>
            t.communication_provider_type === "SMS",
        ).length,
        email: items.filter(
          (t: any) =>
            t.communication_provider_type === "EMAIL",
        ).length,
      });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDuplicate(id: string) {
    try {
      await communicationsService.duplicateTemplate(id);

      toast.success("Template duplicated.");

      await loadTemplates();
    } catch (error) {
      console.error(error);
      toast.error("Unable to duplicate template.");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this template?")) return;

    try {
      await communicationsService.deleteTemplate(id);

      toast.success("Template deleted.");

      await loadTemplates();
    } catch (error) {
      console.error(error);
      toast.error("Unable to delete template.");
    }
  }

  async function handlePreview(id: string) {
    try {
      const response =
        await communicationsService.previewTemplate(
          id,
          {},
        );

      setPreviewData(response);

      setPreviewOpen(true);
    } catch (error) {
      console.error(error);
    }
  }

  async function toggleStatus(template: any) {
    try {
      if (template.status === "ACTIVE") {
        await communicationsService.disableTemplate(
          template.id,
        );
      } else {
        await communicationsService.enableTemplate(
          template.id,
        );
      }

      toast.success(
        template.status === "ACTIVE"
          ? "Template disabled."
          : "Template enabled.",
      );

      await loadTemplates();
    } catch (error) {
      console.error(error);
      toast.error("Unable to update template.");
    }
  }

  const statCards = [
    {
      title: "Total Templates",
      value: stats.total,
      color: "text-cyan-400",
    },
    {
      title: "WhatsApp",
      value: stats.whatsapp,
      color: "text-green-400",
    },
    {
      title: "SMS",
      value: stats.sms,
      color: "text-amber-400",
    },
    {
      title: "Email",
      value: stats.email,
      color: "text-blue-400",
    },
  ];

  return (
    <div className="space-y-6 p-6">

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">

        <div>

          <p className="text-[10px] font-semibold uppercase tracking-[0.20em] text-green-400">
            Communication
          </p>

          <h1 className="mt-2 text-2xl font-semibold text-white">
            Templates
          </h1>

          <p className="mt-2 text-sm text-[#64748B]">
            Manage reusable communication templates for WhatsApp, SMS and Email.
          </p>

        </div>

        <div className="flex items-center gap-3">

          <button className="flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-4 py-2 text-sm text-white hover:border-blue-500">

            <Filter className="h-4 w-4"/>

            Filters

          </button>

          <Link
            href="/communications/templates/create"
            className="flex items-center gap-2 bg-green-500 px-4 py-2 text-sm font-medium text-black hover:bg-green-400"
          >

            <Plus className="h-4 w-4"/>

            Create Template

          </Link>

        </div>

      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">

        {statCards.map((card) => (
          <div
            key={card.title}
            className="border border-[#202938] bg-[#0D1117] p-5"
          >

            <p className="text-[10px] uppercase tracking-[0.15em] text-[#64748B]">
              {card.title}
            </p>

            <h2 className={`mt-4 text-3xl font-semibold ${card.color}`}>
              {card.value}
            </h2>

          </div>
        ))}

      </div>

      <div className="border border-[#202938] bg-[#0D1117]">

        <div className="flex flex-col gap-4 border-b border-[#202938] p-5 lg:flex-row lg:items-center lg:justify-between">

          <div className="relative w-full max-w-md">

            <Search className="absolute left-3 top-3 h-4 w-4 text-[#64748B]" />

            <input
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              placeholder="Search templates..."
              className="w-full border border-[#202938] bg-[#080B10] py-2 pl-10 pr-4 text-sm text-white outline-none"
            />

          </div>

          <div className="flex items-center gap-3">

            <select
              value={providerFilter}
              onChange={(e) =>
                setProviderFilter(e.target.value)
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >

              <option value="ALL">All Providers</option>

              <option value="WHATSAPP">WhatsApp</option>

              <option value="SMS">SMS</option>

              <option value="EMAIL">Email</option>

            </select>

            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value)
              }
              className="border border-[#202938] bg-[#080B10] px-3 py-2 text-sm text-white"
            >

              <option value="ALL">All Status</option>

              <option value="ACTIVE">Active</option>

              <option value="DRAFT">Draft</option>

              <option value="ARCHIVED">Archived</option>

            </select>

          </div>

        </div>

        <div className="overflow-x-auto">

          <table className="w-full">

            <thead>

              <tr className="border-b border-[#202938] bg-[#080B10] text-left text-[10px] uppercase tracking-[0.15em] text-[#64748B]">

                <th className="px-5 py-4 font-medium">
                  Template
                </th>

                <th className="px-5 py-4 font-medium">
                  Provider
                </th>

                <th className="px-5 py-4 font-medium">
                  Variables
                </th>

                <th className="px-5 py-4 font-medium">
                  Status
                </th>

                <th className="px-5 py-4 font-medium">
                  Updated
                </th>

                <th className="px-5 py-4 text-right font-medium">
                  Actions
                </th>

              </tr>

            </thead>

            <tbody>

              {loading &&
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index}>
                    <td
                      colSpan={6}
                      className="px-5 py-5"
                    >
                      <div className="h-10 animate-pulse rounded bg-[#111827]" />
                    </td>
                  </tr>
                ))}

              {!loading && templates.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="py-12 text-center"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <FileText className="h-10 w-10 text-[#475569]" />

                      <p className="text-sm text-[#94A3B8]">
                        No templates found.
                      </p>

                      <p className="text-xs text-[#64748B]">
                        Create your first communication
                        template.
                      </p>
                    </div>
                  </td>
                </tr>
              )}

              {!loading && templates.map((template) => (

                <tr
                  key={template.id}
                  className="border-b border-[#202938] transition-colors hover:bg-[#080B10]"
                >

                  <td className="px-5 py-4">

                    <div className="flex items-center gap-4">

                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#202938] bg-[#111827]">

                        {template.communication_provider_type === "WHATSAPP" && (
                          <MessageCircle className="h-5 w-5 text-green-400" />
                        )}

                        {template.communication_provider_type === "SMS" && (
                          <Smartphone className="h-5 w-5 text-amber-400" />
                        )}

                        {template.communication_provider_type === "EMAIL" && (
                          <Mail className="h-5 w-5 text-blue-400" />
                        )}

                      </div>

                      <div>

                        <h3 className="font-medium text-white">
                          {template.name}
                        </h3>

                        <p className="mt-1 text-xs text-[#64748B]">
                          Template #{template.id}
                        </p>

                      </div>

                    </div>

                  </td>

                  <td className="px-5 py-4">

                    <span className="text-sm text-[#CBD5E1]">
                      {template.communication_provider_name}
                    </span>

                  </td>

                  <td className="px-5 py-4">

                    <div className="flex flex-wrap gap-2">

                      {template.variables?.map(
                        (variable: string) => (
                          <span
                            key={variable}
                            className="rounded-md border border-[#202938] bg-[#111827] px-2 py-1 text-[11px] text-cyan-400"
                          >
                            {variable}
                          </span>
                        ),
                      )}

                    </div>

                  </td>

                  <td className="px-5 py-4">

                    <span
                      onClick={() => toggleStatus(template)}
                      className={`inline-flex cursor-pointer rounded-full px-3 py-1 text-xs font-medium ${
                        template.status === "ACTIVE"
                          ? "bg-green-500/15 text-green-400"
                          : "bg-amber-500/15 text-amber-400"
                      }`}
                    >
                      {template.status}
                    </span>

                  </td>

                  <td className="px-5 py-4 text-sm text-[#94A3B8]">

                    {new Date(
                      template.updated_at,
                    ).toLocaleDateString()}

                  </td>

                  <td className="px-5 py-4">

                    <div className="flex justify-end gap-2">

                      <button
                        onClick={() => handlePreview(template.id)}
                        className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-cyan-500"
                      >

                        <Eye className="h-4 w-4 text-cyan-400" />

                      </button>

                      <Link
                        href={`/communications/templates/${template.id}`}
                        className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-blue-500"
                      >
                        <Pencil className="h-4 w-4 text-blue-400" />
                      </Link>

                      <button
                        onClick={() => handleDuplicate(template.id)}
                        className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-amber-500"
                      >

                        <Copy className="h-4 w-4 text-amber-400" />

                      </button>

                      <button
                        onClick={() => handleDelete(template.id)}
                        className="rounded-md border border-[#202938] bg-[#111827] p-2 transition hover:border-red-500"
                      >

                        <Trash2 className="h-4 w-4 text-red-400" />

                      </button>

                    </div>

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </div>

      <Dialog
        open={previewOpen}
        onOpenChange={setPreviewOpen}
      >
        <DialogContent className="max-w-2xl bg-[#0D1117] border-[#202938]">

          <DialogHeader>
            <DialogTitle>
              Template Preview
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">

            <div>

              <p className="text-xs text-[#64748B]">
                Subject
              </p>

              <p className="text-white">
                {previewData?.subject}
              </p>

            </div>

            <div>

              <p className="text-xs text-[#64748B]">
                Message
              </p>

              <pre className="whitespace-pre-wrap rounded-md bg-[#080B10] p-4 text-sm text-white">
{previewData?.body}
              </pre>

            </div>

          </div>

        </DialogContent>
      </Dialog>

    </div>
  );
}
