"use client";

import { useState } from "react";
import { Edit2, Plug, Plus, X } from "lucide-react";

import { networkService } from "@/services/network.service";
import type {
  NetworkNode,
  NetworkNodePayload,
  NetworkNodeType,
  PointOfPresence,
  ProvisioningBackend,
} from "@/types/network";

interface NetworkNodesTableProps {
  nodes: NetworkNode[];
  pops: PointOfPresence[];
  onRefresh: () => void;
}

const NODE_TYPE_LABELS: Record<NetworkNodeType, string> = {
  ROUTER: "Router",
  OLT: "OLT",
  SWITCH: "Switch",
  ACCESS_POINT: "Access Point",
  OTHER: "Other",
};

const EMPTY_FORM: NetworkNodePayload = {
  name: "",
  code: "",
  node_type: "ROUTER",
  pop_site: null,
  management_ip: null,
  location: "",
  is_active: true,
  provisioning_backend: "MANUAL",
  router_api_host: "",
  router_api_port: null,
  router_api_username: "",
  router_api_password: "",
  router_api_use_tls: false,
};

export default function NetworkNodesTable({
  nodes,
  pops,
  onRefresh,
}: NetworkNodesTableProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<NetworkNode | null>(null);
  const [formData, setFormData] = useState<NetworkNodePayload>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<{ ok: boolean; message: string } | null>(null);

  const handleOpenCreate = () => {
    setEditingNode(null);
    setFormData(EMPTY_FORM);
    setFormError(null);
    setConnectionResult(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (node: NetworkNode) => {
    setEditingNode(node);
    setFormData({
      name: node.name,
      code: node.code,
      node_type: node.node_type,
      pop_site: node.pop_site ?? null,
      management_ip: node.management_ip,
      location: node.location || "",
      is_active: node.is_active,
      provisioning_backend: node.provisioning_backend,
      router_api_host: node.router_api_host || "",
      router_api_port: node.router_api_port,
      router_api_username: node.router_api_username || "",
      router_api_password: "",
      router_api_use_tls: node.router_api_use_tls,
    });
    setFormError(null);
    setConnectionResult(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    const payload: NetworkNodePayload = {
      ...formData,
      management_ip: formData.management_ip?.trim() || null,
    };
    // Omit a blank password so editing other fields keeps the stored router login.
    if (!payload.router_api_password) {
      delete payload.router_api_password;
    }

    try {
      if (editingNode) {
        await networkService.updateNode(editingNode.id, payload);
      } else {
        await networkService.createNode(payload);
      }
      setIsModalOpen(false);
      onRefresh();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to save network node.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleTestConnection = async () => {
    if (!editingNode) return;
    setTestingConnection(true);
    setConnectionResult(null);

    try {
      const result = await networkService.testNodeConnection(editingNode.id);
      setConnectionResult({
        ok: true,
        message: `Connected to ${result.router.identity || "router"} · RouterOS ${result.router.version} · ${result.router.board_name}`,
      });
    } catch (err) {
      setConnectionResult({
        ok: false,
        message: err instanceof Error ? err.message : "Router connection failed.",
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const isMikroTik = formData.provisioning_backend === "MIKROTIK";

  return (
    <section className="border border-[#202938] bg-[#0D1117]">
      <div className="flex items-start justify-between gap-3 border-b border-[#202938] px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold text-[#F8FAFC]">
            Network Nodes
          </h2>

          <p className="mt-1 text-xs text-[#64748B]">
            Registered infrastructure and active service assignments
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="flex items-center gap-2 border border-[#38BDF8] bg-[#38BDF8]/10 px-4 py-2 text-xs font-semibold text-[#38BDF8] transition-colors hover:bg-[#38BDF8]/20"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Node
        </button>
      </div>

      {nodes.length === 0 ? (
        <div className="flex min-h-56 flex-col items-center justify-center gap-2 p-6">
          <p className="text-xs text-[#64748B]">
            No network nodes are registered.
          </p>

          <p className="text-[11px] text-[#64748B]">
            Add a router, OLT or switch to start activating customers.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left">
            <thead>
              <tr className="border-b border-[#202938] bg-[#121821]/50">
                <th className="px-5 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Node
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Type
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Status
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Management IP
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Location
                </th>

                <th className="px-4 py-3 text-[10px] font-medium uppercase tracking-wider text-[#64748B]">
                  Assignments
                </th>

                <th className="px-4 py-3" />
              </tr>
            </thead>

            <tbody>
              {nodes.map((node) => (
                <tr
                  key={node.id}
                  className="border-b border-[#202938] transition-colors last:border-b-0 hover:bg-[#121821]/70"
                >
                  <td className="px-5 py-4">
                    <p className="text-sm font-medium text-[#F8FAFC]">
                      {node.name}
                    </p>

                    <p className="mt-1 font-mono text-[10px] text-[#64748B]">
                      {node.code}
                      {node.pop_site_name ? ` · ${node.pop_site_name}` : ""}
                    </p>

                    {node.provisioning_backend === "MIKROTIK" && (
                      <span className="mt-1.5 inline-flex items-center gap-1 border border-[#38BDF8]/20 bg-[#38BDF8]/5 px-1.5 py-0.5 text-[10px] text-[#38BDF8]">
                        <Plug className="h-2.5 w-2.5" />
                        MikroTik API
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-4">
                    <span className="border border-[#3B82F6]/20 bg-[#3B82F6]/10 px-2 py-1 text-[10px] font-medium text-[#60A5FA]">
                      {node.node_type.replaceAll("_", " ")}
                    </span>
                  </td>

                  <td className="px-4 py-4">
                    <span
                      className={`inline-flex items-center gap-2 border px-2 py-1 text-[11px] font-medium ${
                        node.is_active
                          ? "border-[#22C55E]/20 bg-[#22C55E]/10 text-[#22C55E]"
                          : "border-[#EF4444]/20 bg-[#EF4444]/10 text-[#EF4444]"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          node.is_active
                            ? "bg-[#22C55E]"
                            : "bg-[#EF4444]"
                        }`}
                      />

                      {node.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>

                  <td className="px-4 py-4 font-mono text-xs text-[#94A3B8]">
                    {node.management_ip ?? "Not configured"}
                  </td>

                  <td className="px-4 py-4 text-xs text-[#94A3B8]">
                    {node.location || "Not specified"}
                  </td>

                  <td className="px-4 py-4 text-sm font-medium text-[#CBD5E1]">
                    {node.assignment_count}
                  </td>

                  <td className="px-4 py-4 text-right">
                    <button
                      type="button"
                      onClick={() => handleOpenEdit(node)}
                      className="inline-flex items-center gap-1 border border-[#202938] bg-[#161B22] px-2.5 py-1 text-[11px] text-[#94A3B8] transition-colors hover:border-[#38BDF8] hover:text-[#38BDF8]"
                    >
                      <Edit2 className="h-3 w-3" />
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">
                {editingNode ? `Edit Network Node: ${editingNode.code}` : "Add New Network Node"}
              </h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-[#64748B] hover:text-[#F8FAFC]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-[#EF4444]/30 bg-[#EF4444]/10 p-2.5 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Node Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. RTR-LHR-01"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 font-mono text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Node Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Gulberg Core Router"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Device Type</label>
                  <select
                    value={formData.node_type}
                    onChange={(e) => setFormData({ ...formData, node_type: e.target.value as NetworkNodeType })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    {(Object.keys(NODE_TYPE_LABELS) as NetworkNodeType[]).map((type) => (
                      <option key={type} value={type}>
                        {NODE_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Status</label>
                  <select
                    value={formData.is_active ? "ACTIVE" : "INACTIVE"}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.value === "ACTIVE" })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">POP Site</label>
                  <select
                    value={formData.pop_site ?? ""}
                    onChange={(e) => setFormData({ ...formData, pop_site: e.target.value || null })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    <option value="">Not assigned</option>
                    {pops.map((pop) => (
                      <option key={pop.id} value={pop.id}>
                        {pop.code} · {pop.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Management IP</label>
                  <input
                    type="text"
                    placeholder="e.g. 10.10.0.1"
                    value={formData.management_ip ?? ""}
                    onChange={(e) => setFormData({ ...formData, management_ip: e.target.value })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 font-mono text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Location</label>
                <input
                  type="text"
                  placeholder="Rack, building or street landmark"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                />
              </div>

              <div className="space-y-3 border-t border-[#202938] pt-4">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">Router Integration</label>
                  <select
                    value={formData.provisioning_backend}
                    onChange={(e) => setFormData({ ...formData, provisioning_backend: e.target.value as ProvisioningBackend })}
                    className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                  >
                    <option value="MANUAL">Manual (no router integration)</option>
                    <option value="MIKROTIK">MikroTik RouterOS API (PPPoE)</option>
                  </select>
                  <p className="mt-1 text-[11px] text-[#64748B]">
                    {isMikroTik
                      ? "Activations, suspensions, restores and package changes are pushed to this router automatically."
                      : "Provisioning is recorded in Nexora only; staff apply changes on the router by hand."}
                  </p>
                </div>

                {isMikroTik && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">API Host</label>
                        <input
                          type="text"
                          placeholder={formData.management_ip || "Defaults to management IP"}
                          value={formData.router_api_host}
                          onChange={(e) => setFormData({ ...formData, router_api_host: e.target.value })}
                          className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 font-mono text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">API Port</label>
                        <input
                          type="number"
                          min="1"
                          max="65535"
                          placeholder={formData.router_api_use_tls ? "8729" : "8728"}
                          value={formData.router_api_port ?? ""}
                          onChange={(e) => setFormData({ ...formData, router_api_port: e.target.value ? Number(e.target.value) : null })}
                          className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 font-mono text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">API Username *</label>
                        <input
                          type="text"
                          required
                          autoComplete="off"
                          placeholder="e.g. nexora-api"
                          value={formData.router_api_username}
                          onChange={(e) => setFormData({ ...formData, router_api_username: e.target.value })}
                          className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] uppercase tracking-wider text-[#64748B]">
                          API Password {editingNode?.router_api_password_set ? "" : "*"}
                        </label>
                        <input
                          type="password"
                          autoComplete="new-password"
                          required={!editingNode?.router_api_password_set}
                          placeholder={editingNode?.router_api_password_set ? "Saved · leave blank to keep" : ""}
                          value={formData.router_api_password ?? ""}
                          onChange={(e) => setFormData({ ...formData, router_api_password: e.target.value })}
                          className="mt-1 w-full border border-[#202938] bg-[#161B22] px-3 py-2 text-xs text-[#F8FAFC] focus:border-[#38BDF8] focus:outline-none"
                        />
                      </div>
                    </div>

                    <label className="flex items-center gap-2 text-[11px] text-[#94A3B8]">
                      <input
                        type="checkbox"
                        checked={formData.router_api_use_tls}
                        onChange={(e) => setFormData({ ...formData, router_api_use_tls: e.target.checked })}
                        className="h-3.5 w-3.5 accent-[#38BDF8]"
                      />
                      Use API-SSL (TLS, port 8729)
                    </label>

                    {editingNode && editingNode.provisioning_backend === "MIKROTIK" && (
                      <div className="space-y-2">
                        <button
                          type="button"
                          onClick={handleTestConnection}
                          disabled={testingConnection}
                          className="inline-flex items-center gap-1.5 border border-[#202938] bg-[#161B22] px-3 py-1.5 text-[11px] text-[#94A3B8] transition-colors hover:border-[#38BDF8] hover:text-[#38BDF8] disabled:opacity-50"
                        >
                          <Plug className="h-3 w-3" />
                          {testingConnection ? "Testing..." : "Test Router Connection"}
                        </button>

                        {connectionResult && (
                          <p className={`text-[11px] ${connectionResult.ok ? "text-[#22C55E]" : "text-[#EF4444]"}`}>
                            {connectionResult.message}
                          </p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {editingNode && editingNode.assignment_count > 0 && (
                <p className="text-[11px] text-[#64748B]">
                  This node carries {editingNode.assignment_count} active service assignment(s) and cannot be deactivated until they are moved.
                </p>
              )}

              <div className="flex flex-wrap items-center justify-end gap-3 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="border border-[#202938] bg-[#161B22] px-4 py-2 text-xs text-[#94A3B8] hover:text-[#F8FAFC]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-[#38BDF8] bg-[#38BDF8] px-4 py-2 text-xs font-semibold text-[#0D1117] hover:bg-[#38BDF8]/90 disabled:opacity-50"
                >
                  {submitting ? "Saving..." : editingNode ? "Update Node" : "Create Node"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
