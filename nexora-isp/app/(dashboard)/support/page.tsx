"use client";

import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Clock3,
  ExternalLink,
  Eye,
  FileText,
  Filter,
  Flame,
  LifeBuoy,
  Loader2,
  Lock,
  MessageSquare,
  Network,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  Sliders,
  Star,
  Tag,
  Ticket,
  UserCheck,
  UserPlus,
  Users,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { customersService } from "@/services/customers.service";
import { staffService, OrganizationStaff } from "@/services/staff-service";
import {
  Complaint,
  ComplaintCategory,
  ComplaintInternalNote,
  ComplaintPriority,
  ComplaintSLAPolicy,
  ComplaintSource,
  ComplaintStatus,
  ComplaintTimelineEvent,
  CustomerConfirmation,
  Incident,
  IncidentStatus,
  SLAStatus,
  SupportDashboardMetrics,
  supportService,
} from "@/services/support.service";

function formatDate(value: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("en-PK", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  color = "blue",
}: {
  label: string;
  value: number | string;
  description: string;
  icon: any;
  color?: "blue" | "amber" | "rose" | "emerald" | "purple" | "indigo";
}) {
  const colorMap = {
    blue: "text-blue-400 border-blue-500/20 bg-blue-500/5",
    amber: "text-amber-400 border-amber-500/20 bg-amber-500/5",
    rose: "text-rose-400 border-rose-500/20 bg-rose-500/5",
    emerald: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
    purple: "text-purple-400 border-purple-500/20 bg-purple-500/5",
    indigo: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
  };

  return (
    <div className="border border-[#202938] bg-[#0D1117] p-4 transition-all hover:border-[#303E55]">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#64748B]">
            {label}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-[#F8FAFC]">
            {value}
          </p>
        </div>
        <div className={`flex h-9 w-9 items-center justify-center border ${colorMap[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 border-t border-[#202938] pt-2 text-[11px] text-[#64748B]">
        {description}
      </p>
    </div>
  );
}

function getPriorityBadge(priority: ComplaintPriority) {
  switch (priority) {
    case "CRITICAL":
      return (
        <span className="inline-flex items-center gap-1 border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-rose-400">
          <Flame className="h-3 w-3" /> Critical
        </span>
      );
    case "HIGH":
      return (
        <span className="inline-flex items-center gap-1 border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-400">
          <AlertTriangle className="h-3 w-3" /> High
        </span>
      );
    case "MEDIUM":
      return (
        <span className="inline-flex items-center gap-1 border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-blue-400">
          Medium
        </span>
      );
    case "LOW":
      return (
        <span className="inline-flex items-center gap-1 border border-slate-700 bg-slate-800/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Low
        </span>
      );
  }
}

function getStatusBadge(status: ComplaintStatus) {
  switch (status) {
    case "NEW":
    case "OPEN":
      return (
        <span className="inline-flex items-center gap-1 border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400">
          <Clock className="h-3 w-3" /> {status}
        </span>
      );
    case "ASSIGNED":
      return (
        <span className="inline-flex items-center gap-1 border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
          <UserCheck className="h-3 w-3" /> Assigned
        </span>
      );
    case "IN_PROGRESS":
      return (
        <span className="inline-flex items-center gap-1 border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
          <RefreshCw className="h-3 w-3 animate-spin" /> In Progress
        </span>
      );
    case "WAITING_CUSTOMER":
      return (
        <span className="inline-flex items-center gap-1 border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-400">
          Waiting Customer
        </span>
      );
    case "WAITING_PARTS":
      return (
        <span className="inline-flex items-center gap-1 border border-orange-500/30 bg-orange-500/10 px-2 py-0.5 text-[10px] font-medium text-orange-400">
          Waiting Parts
        </span>
      );
    case "ESCALATED":
      return (
        <span className="inline-flex items-center gap-1 border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 text-[10px] font-bold text-rose-400">
          <ShieldAlert className="h-3 w-3" /> Escalated
        </span>
      );
    case "RESOLVED":
      return (
        <span className="inline-flex items-center gap-1 border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
          <CheckCircle2 className="h-3 w-3" /> Resolved
        </span>
      );
    case "CUSTOMER_CONFIRMED":
    case "CLOSED":
      return (
        <span className="inline-flex items-center gap-1 border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium text-slate-400">
          <Lock className="h-3 w-3" /> {status}
        </span>
      );
    case "CANCELLED":
      return (
        <span className="inline-flex items-center gap-1 border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
          Cancelled
        </span>
      );
  }
}

function getSLABadge(complaint: Complaint) {
  if (complaint.status === "RESOLVED" || complaint.status === "CLOSED" || complaint.status === "CUSTOMER_CONFIRMED") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400">
        <CheckCircle2 className="h-3 w-3" /> SLA Met
      </span>
    );
  }

  if (complaint.is_resolution_sla_breached || complaint.sla_status === "BREACHED") {
    return (
      <span className="inline-flex items-center gap-1 border border-rose-500/40 bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-bold text-rose-300 animate-pulse">
        <AlertTriangle className="h-3 w-3" /> Breached
      </span>
    );
  }

  if (complaint.resolution_due_at) {
    const dueTime = new Date(complaint.resolution_due_at).getTime();
    const now = Date.now();
    const diffHours = (dueTime - now) / (1000 * 3600);

    if (diffHours <= 2 && diffHours > 0) {
      return (
        <span className="inline-flex items-center gap-1 border border-amber-500/30 bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-300">
          <Clock className="h-3 w-3" /> Due in {Math.round(diffHours * 60)}m
        </span>
      );
    }
    if (diffHours < 0) {
      return (
        <span className="inline-flex items-center gap-1 border border-rose-500/40 bg-rose-500/20 px-1.5 py-0.5 text-[10px] font-bold text-rose-300">
          Overdue
        </span>
      );
    }
  }

  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
      <Clock className="h-3 w-3" /> On Track
    </span>
  );
}

const DIAGNOSIS_CATEGORIES = [
  "Fiber Splice Repaired",
  "Fiber Patch Cord Replaced",
  "ONU Optical Joint Corrected",
  "ONU / Optical Device Replaced",
  "Router Reconfigured / Reset",
  "Router Hardware Replaced",
  "Speed Profile Refreshed on BRAS",
  "IP / Gateway Configuration Corrected",
  "RJ45 Connector Replaced",
  "Power Supply / Adapter Replaced",
  "Customer Premises Wiring Corrected",
  "Customer LAN Device Fault Found",
  "Distribution Node Card Reset",
  "Other Technical Fix",
];

export default function SupportPage() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<SupportDashboardMetrics | null>(null);
  const [slaPolicies, setSlaPolicies] = useState<ComplaintSLAPolicy[]>([]);
  const [staffList, setStaffList] = useState<OrganizationStaff[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"TICKETS" | "WORKLOAD" | "INCIDENTS" | "SLA_POLICIES">("TICKETS");
  const [ticketFilter, setTicketFilter] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  // Modals & Drawer State
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [isNewTicketOpen, setIsNewTicketOpen] = useState(false);
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const [isTransitionOpen, setIsTransitionOpen] = useState(false);
  const [isEscalateOpen, setIsEscalateOpen] = useState(false);
  const [isResolveOpen, setIsResolveOpen] = useState(false);
  const [isCloseOpen, setIsCloseOpen] = useState(false);

  // Form Submissions
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [newNote, setNewNote] = useState("");

  // Assign Form
  const [selectedTechId, setSelectedTechId] = useState("");
  const [assignReason, setAssignReason] = useState("");
  const [assignNotes, setAssignNotes] = useState("");

  // Transition Form
  const [targetStatus, setTargetStatus] = useState<ComplaintStatus>("IN_PROGRESS");
  const [transitionNotes, setTransitionNotes] = useState("");

  // Escalate Form
  const [escalateReason, setEscalateReason] = useState("");
  const [escalateToId, setEscalateToId] = useState("");

  // Resolve Form
  const [diagnosisCategory, setDiagnosisCategory] = useState(DIAGNOSIS_CATEGORIES[0]);
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Close Form
  const [confirmation, setConfirmation] = useState<CustomerConfirmation>("CONFIRMED");
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackNotes, setFeedbackNotes] = useState("");

  // New Complaint Registration
  const [customerSearch, setCustomerSearch] = useState("");
  const [customers, setCustomers] = useState<any[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [newCategory, setNewCategory] = useState<ComplaintCategory>("CONNECTIVITY");
  const [newPriority, setNewPriority] = useState<ComplaintPriority>("MEDIUM");
  const [newSource, setNewSource] = useState<ComplaintSource>("PHONE");
  const [newSubject, setNewSubject] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [initialTechId, setInitialTechId] = useState("");

  const loadData = useCallback(async (background = false) => {
    try {
      if (background) setRefreshing(true);
      else setLoading(true);

      const [complaintsRes, incidentsRes, metricsRes, slaRes, staffRes] = await Promise.all([
        supportService.getComplaints(),
        supportService.getIncidents(),
        supportService.getDashboardMetrics(),
        supportService.getSLAPolicies(),
        staffService.getStaff(),
      ]);

      setComplaints(complaintsRes);
      setIncidents(incidentsRes);
      setMetrics(metricsRes);
      setSlaPolicies(slaRes);
      setStaffList(staffRes);
    } catch (err) {
      console.error("Failed to load support operations:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load customer list when opening new ticket modal
  useEffect(() => {
    if (isNewTicketOpen) {
      customersService.getCustomers({ limit: 100 } as any).then(setCustomers).catch(console.error);
    }
  }, [isNewTicketOpen]);

  // Refresh single complaint for Drawer
  const refreshSelectedComplaint = async (complaintId: string) => {
    try {
      const updated = await supportService.getComplaintDetail(complaintId);
      setSelectedComplaint(updated);
      setComplaints((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      const freshMetrics = await supportService.getDashboardMetrics();
      setMetrics(freshMetrics);
    } catch (err) {
      console.error("Failed to refresh ticket detail:", err);
    }
  };

  // Filtered complaints
  const filteredComplaints = useMemo(() => {
    return complaints.filter((c) => {
      if (ticketFilter === "OPEN") {
        if (!["NEW", "OPEN", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS", "WAITING_CUSTOMER", "WAITING_PARTS", "ESCALATED"].includes(c.status)) return false;
      } else if (ticketFilter === "IN_PROGRESS") {
        if (c.status !== "IN_PROGRESS") return false;
      } else if (ticketFilter === "SLA_BREACHED") {
        if (!c.is_resolution_sla_breached && c.sla_status !== "BREACHED") return false;
      } else if (ticketFilter === "UNASSIGNED") {
        if (c.assigned_to_id || !["NEW", "OPEN", "ACKNOWLEDGED"].includes(c.status)) return false;
      } else if (ticketFilter === "ESCALATED") {
        if (!c.is_escalated && c.status !== "ESCALATED") return false;
      } else if (ticketFilter === "RESOLVED") {
        if (!["RESOLVED", "CUSTOMER_CONFIRMED", "CLOSED"].includes(c.status)) return false;
      }

      if (priorityFilter && c.priority !== priorityFilter) return false;
      if (categoryFilter && c.category !== categoryFilter) return false;

      if (search.trim()) {
        const q = search.toLowerCase();
        return (
          c.complaint_number.toLowerCase().includes(q) ||
          c.customer_name.toLowerCase().includes(q) ||
          c.customer_phone.toLowerCase().includes(q) ||
          c.subject.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          (c.service_number && c.service_number.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [complaints, ticketFilter, priorityFilter, categoryFilter, search]);

  // Handlers
  const handleCreateComplaint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCustomerId || !newSubject.trim() || !newDescription.trim()) {
      setFormError("Please select a customer and fill in subject and description.");
      return;
    }

    try {
      setSubmitting(true);
      setFormError("");
      const created = await supportService.createComplaint({
        customer_id: selectedCustomerId,
        category: newCategory,
        priority: newPriority,
        source: newSource,
        subject: newSubject.trim(),
        description: newDescription.trim(),
        assigned_to_id: initialTechId || null,
      });

      setIsNewTicketOpen(false);
      setNewSubject("");
      setNewDescription("");
      setSelectedCustomerId("");
      setInitialTechId("");
      await loadData(true);
      setSelectedComplaint(created);
    } catch (err: any) {
      setFormError(err?.message || "Failed to create complaint.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || !selectedTechId) return;

    try {
      setSubmitting(true);
      setFormError("");
      if (selectedComplaint.assigned_to_id) {
        // Reassignment
        if (!assignReason.trim()) {
          setFormError("Reassignment reason is required.");
          setSubmitting(false);
          return;
        }
        await supportService.reassignComplaint(selectedComplaint.id, selectedTechId, assignReason.trim(), assignNotes.trim());
      } else {
        // Initial assignment
        await supportService.assignComplaint(selectedComplaint.id, selectedTechId, assignNotes.trim());
      }
      setIsAssignOpen(false);
      setAssignReason("");
      setAssignNotes("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      setFormError(err?.message || "Failed to assign technician.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleTransitionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint) return;

    try {
      setSubmitting(true);
      setFormError("");
      await supportService.transitionComplaint(selectedComplaint.id, targetStatus, transitionNotes.trim());
      setIsTransitionOpen(false);
      setTransitionNotes("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      setFormError(err?.message || "Failed to transition ticket status.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEscalateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || !escalateReason.trim()) {
      setFormError("Escalation reason is required.");
      return;
    }

    try {
      setSubmitting(true);
      setFormError("");
      await supportService.escalateComplaint(selectedComplaint.id, escalateReason.trim(), escalateToId || null);
      setIsEscalateOpen(false);
      setEscalateReason("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      setFormError(err?.message || "Failed to escalate ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || !resolutionSummary.trim()) {
      setFormError("Resolution summary is required.");
      return;
    }

    try {
      setSubmitting(true);
      setFormError("");
      await supportService.resolveComplaint(
        selectedComplaint.id,
        diagnosisCategory,
        resolutionSummary.trim(),
        resolutionNotes.trim()
      );
      setIsResolveOpen(false);
      setResolutionSummary("");
      setResolutionNotes("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      setFormError(err?.message || "Failed to resolve ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint) return;

    try {
      setSubmitting(true);
      setFormError("");
      await supportService.closeComplaint(selectedComplaint.id, confirmation, feedbackRating, feedbackNotes.trim());
      setIsCloseOpen(false);
      setFeedbackNotes("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      setFormError(err?.message || "Failed to close ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddNote = async () => {
    if (!selectedComplaint || !newNote.trim()) return;
    try {
      setSubmitting(true);
      await supportService.addInternalNote(selectedComplaint.id, newNote.trim());
      setNewNote("");
      await refreshSelectedComplaint(selectedComplaint.id);
    } catch (err: any) {
      alert(err?.message || "Failed to add internal note.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 border-b border-[#202938] pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-ping" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-blue-400">
              Customer Support & Technical Operations
            </p>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#F8FAFC]">
            Support Operations & Helpdesk
          </h1>
          <p className="mt-1 text-xs text-[#94A3B8]">
            Multi-channel ticket management, technician dispatching, automated SLA enforcement, and technical diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 border border-[#202938] bg-[#0D1117] px-3.5 py-2 text-xs font-medium text-[#94A3B8] transition-colors hover:border-[#303E55] hover:text-[#F8FAFC] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin text-blue-400" : ""}`} />
            Refresh
          </button>

          <button
            onClick={() => setIsNewTicketOpen(true)}
            className="inline-flex items-center gap-2 border border-blue-500 bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-blue-600/20 transition-all hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" />
            Register New Ticket
          </button>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard
          label="Open Tickets"
          value={metrics?.open_complaints ?? 0}
          description="Total active queue"
          icon={Ticket}
          color="blue"
        />
        <MetricCard
          label="Critical Outages"
          value={metrics?.critical_complaints ?? 0}
          description="High impact tickets"
          icon={Flame}
          color="rose"
        />
        <MetricCard
          label="SLA Breached"
          value={metrics?.sla_breached_complaints ?? 0}
          description="Overdue resolution"
          icon={AlertTriangle}
          color="amber"
        />
        <MetricCard
          label="Unassigned"
          value={metrics?.unassigned_complaints ?? 0}
          description="Awaiting assignment"
          icon={UserPlus}
          color="purple"
        />
        <MetricCard
          label="In Progress"
          value={metrics?.in_progress_complaints ?? 0}
          description="Field & NOC actions"
          icon={RefreshCw}
          color="indigo"
        />
        <MetricCard
          label="Avg Resolution"
          value={`${metrics?.avg_resolution_hours ?? 0}h`}
          description="Mean turnaround time"
          icon={Clock3}
          color="emerald"
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#202938]">
        <button
          onClick={() => setActiveTab("TICKETS")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "TICKETS"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-[#64748B] hover:text-[#94A3B8]"
          }`}
        >
          <LifeBuoy className="h-4 w-4" />
          Tickets & Complaints ({filteredComplaints.length})
        </button>

        <button
          onClick={() => setActiveTab("WORKLOAD")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "WORKLOAD"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-[#64748B] hover:text-[#94A3B8]"
          }`}
        >
          <Users className="h-4 w-4" />
          Technician Workloads ({metrics?.technician_workloads?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab("INCIDENTS")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "INCIDENTS"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-[#64748B] hover:text-[#94A3B8]"
          }`}
        >
          <Network className="h-4 w-4" />
          Network Incidents & Outages ({incidents.length})
        </button>

        <button
          onClick={() => setActiveTab("SLA_POLICIES")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "SLA_POLICIES"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-[#64748B] hover:text-[#94A3B8]"
          }`}
        >
          <Sliders className="h-4 w-4" />
          SLA Configuration
        </button>
      </div>

      {/* Tab 1: Tickets & Complaints */}
      {activeTab === "TICKETS" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col gap-3 rounded border border-[#202938] bg-[#0D1117] p-3 md:flex-row md:items-center md:justify-between">
            {/* Quick Status Filter Pills */}
            <div className="flex flex-wrap gap-1.5">
              {[
                { id: "ALL", label: "All Tickets" },
                { id: "OPEN", label: "Active Queue" },
                { id: "IN_PROGRESS", label: "In Progress" },
                { id: "SLA_BREACHED", label: "SLA Breached" },
                { id: "UNASSIGNED", label: "Unassigned" },
                { id: "ESCALATED", label: "Escalated" },
                { id: "RESOLVED", label: "Resolved/Closed" },
              ].map((pill) => (
                <button
                  key={pill.id}
                  onClick={() => setTicketFilter(pill.id)}
                  className={`px-3 py-1 text-[11px] font-medium transition-all ${
                    ticketFilter === pill.id
                      ? "border border-blue-500/40 bg-blue-600 text-white"
                      : "border border-[#202938] bg-[#121821] text-[#94A3B8] hover:border-[#303E55] hover:text-white"
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* Search & Select Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search ticket, customer, phone..."
                  className="w-48 sm:w-60 border border-[#202938] bg-[#121821] pl-8 pr-3 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-blue-500 focus:outline-none"
                />
              </div>

              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="border border-[#202938] bg-[#121821] px-2.5 py-1 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="border border-[#202938] bg-[#121821] px-2.5 py-1 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
              >
                <option value="">All Categories</option>
                <option value="CONNECTIVITY">Connectivity</option>
                <option value="SPEED">Speed Issue</option>
                <option value="FIBER_CABLE_DAMAGE">Fiber / Cable</option>
                <option value="ONU_ISSUE">ONU / Optical</option>
                <option value="ROUTER_ISSUE">Router Issue</option>
                <option value="BILLING">Billing</option>
                <option value="CONFIGURATION">Configuration</option>
              </select>
            </div>
          </div>

          {/* Ticket Table */}
          <div className="overflow-hidden border border-[#202938] bg-[#0D1117]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#202938] bg-[#121821] text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">
                <tr>
                  <th className="px-4 py-3">Ticket #</th>
                  <th className="px-4 py-3">Customer & Service</th>
                  <th className="px-4 py-3">Category & Subject</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">SLA Status</th>
                  <th className="px-4 py-3">Assigned Tech</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#202938]">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#64748B]">
                      <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-400" />
                      <p className="mt-2 text-xs">Loading support complaints...</p>
                    </td>
                  </tr>
                ) : filteredComplaints.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#64748B]">
                      <LifeBuoy className="mx-auto h-8 w-8 text-[#303E55]" />
                      <p className="mt-2 text-sm font-medium text-[#94A3B8]">No support tickets found</p>
                      <p className="text-xs text-[#64748B]">Adjust filters or register a new ticket above.</p>
                    </td>
                  </tr>
                ) : (
                  filteredComplaints.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedComplaint(c)}
                      className="cursor-pointer transition-colors hover:bg-[#161F2E]"
                    >
                      <td className="px-4 py-3 font-mono font-bold text-blue-400">
                        {c.complaint_number}
                        {c.is_escalated && (
                          <span className="ml-1.5 inline-block text-[10px] font-bold text-rose-400" title="Escalated Ticket">
                            ▲ L{c.escalation_level}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-[#F8FAFC]">{c.customer_name}</p>
                        <p className="text-[11px] text-[#64748B]">
                          {c.customer_phone} {c.service_number ? `• ${c.service_number}` : ""}
                        </p>
                      </td>
                      <td className="max-w-xs px-4 py-3">
                        <span className="text-[10px] uppercase font-semibold text-slate-400">
                          {c.category.replace(/_/g, " ")}
                        </span>
                        <p className="truncate text-xs text-[#E2E8F0]">{c.subject}</p>
                      </td>
                      <td className="px-4 py-3">{getPriorityBadge(c.priority)}</td>
                      <td className="px-4 py-3">{getStatusBadge(c.status)}</td>
                      <td className="px-4 py-3">{getSLABadge(c)}</td>
                      <td className="px-4 py-3 text-xs text-[#94A3B8]">
                        {c.assigned_to_name ? (
                          <span className="inline-flex items-center gap-1.5 text-[#E2E8F0]">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600/30 text-[9px] font-bold text-blue-300">
                              {c.assigned_to_name.charAt(0).toUpperCase()}
                            </span>
                            {c.assigned_to_name}
                          </span>
                        ) : (
                          <span className="text-amber-400/80 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedComplaint(c);
                          }}
                          className="inline-flex items-center gap-1 border border-[#202938] bg-[#121821] px-2.5 py-1 text-[11px] text-blue-400 hover:border-blue-500 hover:text-white"
                        >
                          <Eye className="h-3 w-3" /> View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Technician Workloads */}
      {activeTab === "WORKLOAD" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {metrics?.technician_workloads?.map((tech) => (
            <div
              key={tech.technician_id}
              className="border border-[#202938] bg-[#0D1117] p-5 transition-all hover:border-[#303E55]"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded border border-blue-500/20 bg-blue-500/10 font-bold text-blue-400">
                    {tech.technician_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-bold text-[#F8FAFC]">{tech.technician_name}</h3>
                    <p className="text-[11px] text-[#64748B]">{tech.email}</p>
                  </div>
                </div>
                <span className="border border-[#202938] bg-[#121821] px-2 py-0.5 text-[10px] font-semibold text-slate-400">
                  {tech.role}
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 border-t border-[#202938] pt-4">
                <div>
                  <p className="text-[10px] uppercase font-semibold text-[#64748B]">Active Assigned Tickets</p>
                  <p className="mt-1 text-xl font-bold text-blue-400">{tech.open_tickets}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase font-semibold text-[#64748B]">Workload Status</p>
                  <p className="mt-1 text-xs font-semibold">
                    {tech.open_tickets === 0 ? (
                      <span className="text-emerald-400">Available</span>
                    ) : tech.open_tickets < 5 ? (
                      <span className="text-blue-400">Normal Load</span>
                    ) : (
                      <span className="text-amber-400">High Workload</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Incidents & Outages */}
      {activeTab === "INCIDENTS" && (
        <div className="space-y-4">
          <div className="overflow-hidden border border-[#202938] bg-[#0D1117]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#202938] bg-[#121821] text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">
                <tr>
                  <th className="px-4 py-3">Incident #</th>
                  <th className="px-4 py-3">Title & Summary</th>
                  <th className="px-4 py-3">Network Node</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Affected Services</th>
                  <th className="px-4 py-3">Started At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#202938]">
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-[#64748B]">
                      <Network className="mx-auto h-8 w-8 text-[#303E55]" />
                      <p className="mt-2 text-sm font-medium text-[#94A3B8]">No active network incidents</p>
                    </td>
                  </tr>
                ) : (
                  incidents.map((inc) => (
                    <tr key={inc.id} className="hover:bg-[#161F2E]">
                      <td className="px-4 py-3 font-mono font-bold text-rose-400">{inc.incident_number}</td>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-[#F8FAFC]">{inc.title}</p>
                        <p className="text-[11px] text-[#64748B]">{inc.description}</p>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-300">
                        {inc.network_node_name || "General Network"}
                      </td>
                      <td className="px-4 py-3">
                        <span className="border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-400">
                          {inc.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-300">
                          {inc.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold text-blue-400">
                        {inc.affected_services?.length ?? 0} Services
                      </td>
                      <td className="px-4 py-3 text-[#64748B]">{formatDate(inc.started_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: SLA Configuration */}
      {activeTab === "SLA_POLICIES" && (
        <div className="max-w-4xl space-y-4">
          <div className="border border-[#202938] bg-[#0D1117] p-6">
            <h2 className="text-base font-bold text-[#F8FAFC]">Configured Priority SLA Policies</h2>
            <p className="mt-1 text-xs text-[#64748B]">
              Tenant-level response and resolution targets. Overrides default ISP thresholds automatically.
            </p>

            <div className="mt-6 space-y-4">
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((p) => {
                const pol = slaPolicies.find((item) => item.priority === p);
                return (
                  <div key={p} className="flex items-center justify-between border border-[#202938] bg-[#121821] p-4">
                    <div className="flex items-center gap-3">
                      {getPriorityBadge(p as ComplaintPriority)}
                      <div>
                        <p className="text-xs font-semibold text-[#F8FAFC]">Priority {p}</p>
                        <p className="text-[11px] text-[#64748B]">
                          First Response: {pol ? pol.response_target_minutes : p === "CRITICAL" ? 15 : p === "HIGH" ? 30 : 60} mins |
                          Resolution: {pol ? pol.resolution_target_hours : p === "CRITICAL" ? 4 : p === "HIGH" ? 8 : 24} hours
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Policy Enforced
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ==================== TICKET DETAIL DRAWER ==================== */}
      {selectedComplaint && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="flex h-full w-full max-w-2xl flex-col border-l border-[#202938] bg-[#0D1117] shadow-2xl">
            {/* Drawer Header */}
            <div className="flex items-start justify-between border-b border-[#202938] bg-[#121821] p-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-base font-bold text-blue-400">
                    {selectedComplaint.complaint_number}
                  </span>
                  {getPriorityBadge(selectedComplaint.priority)}
                  {getStatusBadge(selectedComplaint.status)}
                </div>
                <h2 className="mt-2 text-lg font-bold text-[#F8FAFC]">
                  {selectedComplaint.subject}
                </h2>
                <p className="text-xs text-[#64748B]">
                  Customer: <span className="font-semibold text-slate-300">{selectedComplaint.customer_name}</span> ({selectedComplaint.customer_phone})
                </p>
              </div>

              <button
                onClick={() => setSelectedComplaint(null)}
                className="rounded border border-[#202938] p-1.5 text-[#64748B] hover:border-slate-600 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Quick Action Buttons Bar */}
            <div className="flex flex-wrap items-center gap-2 border-b border-[#202938] bg-[#0D1117] p-3">
              <button
                onClick={() => {
                  setSelectedTechId(selectedComplaint.assigned_to_id || "");
                  setIsAssignOpen(true);
                }}
                className="inline-flex items-center gap-1.5 border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-400 hover:bg-blue-500/20"
              >
                <UserCheck className="h-3.5 w-3.5" />
                {selectedComplaint.assigned_to_id ? "Reassign Tech" : "Assign Tech"}
              </button>

              <button
                onClick={() => {
                  setTargetStatus("IN_PROGRESS");
                  setIsTransitionOpen(true);
                }}
                className="inline-flex items-center gap-1.5 border border-[#202938] bg-[#121821] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-600 hover:text-white"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Update Status
              </button>

              <button
                onClick={() => setIsEscalateOpen(true)}
                className="inline-flex items-center gap-1.5 border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-400 hover:bg-rose-500/20"
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                Escalate
              </button>

              <button
                onClick={() => setIsResolveOpen(true)}
                className="inline-flex items-center gap-1.5 border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Diagnose & Resolve
              </button>

              {selectedComplaint.status === "RESOLVED" && (
                <button
                  onClick={() => setIsCloseOpen(true)}
                  className="inline-flex items-center gap-1.5 border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs font-semibold text-purple-400 hover:bg-purple-500/20"
                >
                  <Lock className="h-3.5 w-3.5" />
                  Confirm & Close
                </button>
              )}
            </div>

            {/* Drawer Body Scroll */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Ticket Overview Card */}
              <div className="border border-[#202938] bg-[#121821] p-4 space-y-3">
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-[#64748B]">Assigned Technician</span>
                    <p className="mt-0.5 font-medium text-[#F8FAFC]">
                      {selectedComplaint.assigned_to_name || "Unassigned"}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-[#64748B]">Service Account</span>
                    <p className="mt-0.5 font-medium text-[#F8FAFC]">
                      {selectedComplaint.service_number || "Direct Customer Account"}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-[#64748B]">Response SLA Due</span>
                    <p className="mt-0.5 text-[#94A3B8]">{formatDate(selectedComplaint.response_due_at)}</p>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-[#64748B]">Resolution SLA Due</span>
                    <p className="mt-0.5 text-[#94A3B8]">{formatDate(selectedComplaint.resolution_due_at)}</p>
                  </div>
                </div>

                <div className="border-t border-[#202938] pt-3">
                  <span className="text-[10px] uppercase font-semibold text-[#64748B]">Customer Description</span>
                  <p className="mt-1 text-xs leading-relaxed text-[#CBD5E1] bg-[#0D1117] p-3 rounded border border-[#202938]">
                    {selectedComplaint.description}
                  </p>
                </div>

                {selectedComplaint.resolution_summary && (
                  <div className="border-t border-[#202938] pt-3">
                    <span className="text-[10px] uppercase font-semibold text-emerald-400">Technical Resolution</span>
                    <p className="mt-1 text-xs text-emerald-300 font-medium">
                      Diagnosis: {selectedComplaint.diagnosis_category}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-300">
                      {selectedComplaint.resolution_summary}
                    </p>
                  </div>
                )}
              </div>

              {/* Staff Internal Notes Feed */}
              <div className="border border-[#202938] bg-[#121821] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#F8FAFC]">
                    <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
                    Internal Staff Notes ({selectedComplaint.internal_notes?.length ?? 0})
                  </h3>
                  <span className="text-[10px] text-slate-500 font-semibold">Staff Only</span>
                </div>

                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      placeholder="Add an internal investigation note..."
                      className="flex-1 border border-[#202938] bg-[#0D1117] px-3 py-1.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:border-blue-500 focus:outline-none"
                    />
                    <button
                      onClick={handleAddNote}
                      disabled={submitting || !newNote.trim()}
                      className="border border-blue-500 bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                    >
                      <Send className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  {selectedComplaint.internal_notes?.map((n) => (
                    <div key={n.id} className="border-l-2 border-blue-500 bg-[#0D1117] p-2.5 text-xs">
                      <div className="flex items-center justify-between text-[10px] text-[#64748B]">
                        <span className="font-semibold text-slate-300">{n.author_name}</span>
                        <span>{formatDate(n.created_at)}</span>
                      </div>
                      <p className="mt-1 text-slate-300">{n.note}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sequential Audit & Event Timeline */}
              <div className="border border-[#202938] bg-[#121821] p-4 space-y-4">
                <h3 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#F8FAFC]">
                  <Clock className="h-3.5 w-3.5 text-blue-400" />
                  Audit & Event Timeline
                </h3>

                <div className="relative pl-4 space-y-4 border-l border-[#202938]">
                  {selectedComplaint.timeline_events?.map((ev) => (
                    <div key={ev.id} className="relative text-xs">
                      <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border border-blue-500 bg-[#0D1117]" />
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-[#F8FAFC]">{ev.summary}</span>
                        <span className="text-[10px] text-[#64748B]">{formatDate(ev.created_at)}</span>
                      </div>
                      {ev.notes && <p className="mt-0.5 text-[#94A3B8]">{ev.notes}</p>}
                      <p className="text-[10px] text-[#64748B]">Actor: {ev.actor_name || "System"}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================== MODAL: REGISTER NEW TICKET ==================== */}
      {isNewTicketOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="text-base font-bold text-[#F8FAFC]">Register New Support Complaint</h2>
              <button onClick={() => setIsNewTicketOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateComplaint} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Select Customer *
                </label>
                <select
                  value={selectedCustomerId}
                  onChange={(e) => setSelectedCustomerId(e.target.value)}
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  required
                >
                  <option value="">— Select Customer —</option>
                  {customers.map((cust: any) => (
                    <option key={cust.id} value={cust.id}>
                      {cust.customer_number} — {cust.full_name} ({cust.phone})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    Category *
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as ComplaintCategory)}
                    className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  >
                    <option value="CONNECTIVITY">Connectivity</option>
                    <option value="SPEED">Speed Issue</option>
                    <option value="ROUTER_ISSUE">Router Issue</option>
                    <option value="ONU_ISSUE">ONU / Optical</option>
                    <option value="FIBER_CABLE_DAMAGE">Fiber / Cable</option>
                    <option value="POWER_ISSUE">Power Adapter</option>
                    <option value="BILLING">Billing Issue</option>
                    <option value="CONFIGURATION">Configuration</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    Priority *
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as ComplaintPriority)}
                    className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    Source Channel
                  </label>
                  <select
                    value={newSource}
                    onChange={(e) => setNewSource(e.target.value as ComplaintSource)}
                    className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  >
                    <option value="PHONE">Phone Call</option>
                    <option value="WHATSAPP">WhatsApp</option>
                    <option value="SMS">SMS</option>
                    <option value="WALK_IN">Walk-in</option>
                    <option value="STAFF">Staff Registered</option>
                    <option value="CUSTOMER_PORTAL">Customer Portal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    Assign Technician
                  </label>
                  <select
                    value={initialTechId}
                    onChange={(e) => setInitialTechId(e.target.value)}
                    className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  >
                    <option value="">— Leave Unassigned —</option>
                    {staffList.map((st) => (
                      <option key={st.user_id} value={st.user_id}>
                        {st.full_name} ({st.role})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Subject *
                </label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="e.g. Red LOS Light on ONU"
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Description / Customer Problem *
                </label>
                <textarea
                  rows={3}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Detailed explanation of the issue..."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsNewTicketOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-blue-500 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {submitting ? "Registering..." : "Create Ticket"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ASSIGN / REASSIGN ==================== */}
      {isAssignOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="text-base font-bold text-[#F8FAFC]">
                {selectedComplaint.assigned_to_id ? "Reassign Field Technician" : "Assign Technician"}
              </h2>
              <button onClick={() => setIsAssignOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleAssignSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Select Staff / Technician *
                </label>
                <select
                  value={selectedTechId}
                  onChange={(e) => setSelectedTechId(e.target.value)}
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                  required
                >
                  <option value="">— Select Technician —</option>
                  {staffList.map((st) => (
                    <option key={st.user_id} value={st.user_id}>
                      {st.full_name} ({st.role})
                    </option>
                  ))}
                </select>
              </div>

              {selectedComplaint.assigned_to_id && (
                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-amber-400">
                    Reassignment Reason (Mandatory) *
                  </label>
                  <input
                    type="text"
                    value={assignReason}
                    onChange={(e) => setAssignReason(e.target.value)}
                    placeholder="e.g. Previous tech engaged on fiber cut"
                    className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Dispatch Notes
                </label>
                <textarea
                  rows={2}
                  value={assignNotes}
                  onChange={(e) => setAssignNotes(e.target.value)}
                  placeholder="Instructions for the technician..."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsAssignOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-blue-500 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {submitting ? "Saving..." : "Confirm Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: STATUS TRANSITION ==================== */}
      {isTransitionOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="text-base font-bold text-[#F8FAFC]">Update Ticket Status</h2>
              <button onClick={() => setIsTransitionOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleTransitionSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Target Status *
                </label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value as ComplaintStatus)}
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                >
                  <option value="ACKNOWLEDGED">Acknowledged</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="WAITING_CUSTOMER">Waiting for Customer</option>
                  <option value="WAITING_PARTS">Waiting for Parts</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Status Update Notes
                </label>
                <textarea
                  rows={3}
                  value={transitionNotes}
                  onChange={(e) => setTransitionNotes(e.target.value)}
                  placeholder="Details of current state..."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsTransitionOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-blue-500 bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {submitting ? "Updating..." : "Update Status"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ESCALATE ==================== */}
      {isEscalateOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="flex items-center gap-2 text-base font-bold text-rose-400">
                <ShieldAlert className="h-5 w-5" /> Escalate Support Ticket
              </h2>
              <button onClick={() => setIsEscalateOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleEscalateSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-rose-300">
                  Escalation Reason (Mandatory) *
                </label>
                <textarea
                  rows={3}
                  value={escalateReason}
                  onChange={(e) => setEscalateReason(e.target.value)}
                  placeholder="Explain why this ticket requires escalation..."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-rose-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Escalate To Manager / Senior
                </label>
                <select
                  value={escalateToId}
                  onChange={(e) => setEscalateToId(e.target.value)}
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-rose-500 focus:outline-none"
                >
                  <option value="">— Unassigned Escalation Pool —</option>
                  {staffList.map((st) => (
                    <option key={st.user_id} value={st.user_id}>
                      {st.full_name} ({st.operational_role || st.role})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsEscalateOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-rose-500 bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  {submitting ? "Escalating..." : "Confirm Escalation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: RESOLVE ==================== */}
      {isResolveOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="flex items-center gap-2 text-base font-bold text-emerald-400">
                <CheckCircle2 className="h-5 w-5" /> Technical Diagnosis & Resolution
              </h2>
              <button onClick={() => setIsResolveOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleResolveSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
                  Diagnosis Category *
                </label>
                <select
                  value={diagnosisCategory}
                  onChange={(e) => setDiagnosisCategory(e.target.value)}
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-emerald-500 focus:outline-none"
                  required
                >
                  {DIAGNOSIS_CATEGORIES.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Resolution Summary (Sent to Customer) *
                </label>
                <textarea
                  rows={2}
                  value={resolutionSummary}
                  onChange={(e) => setResolutionSummary(e.target.value)}
                  placeholder="e.g. Spliced fiber break at distribution joint. Link optical power verified at -19 dBm."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Internal Resolution Notes
                </label>
                <textarea
                  rows={2}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Additional field notes..."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsResolveOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-emerald-500 bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {submitting ? "Resolving..." : "Mark as Resolved"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: CONFIRM & CLOSE ==================== */}
      {isCloseOpen && selectedComplaint && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md border border-[#202938] bg-[#0D1117] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#202938] pb-3">
              <h2 className="flex items-center gap-2 text-base font-bold text-purple-400">
                <Lock className="h-5 w-5" /> Customer Confirmation & Closure
              </h2>
              <button onClick={() => setIsCloseOpen(false)} className="text-[#64748B] hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-3 border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleCloseSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Customer Confirmation Status *
                </label>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setConfirmation("CONFIRMED")}
                    className={`border p-2.5 text-center font-semibold transition-all ${
                      confirmation === "CONFIRMED"
                        ? "border-emerald-500 bg-emerald-500/15 text-emerald-400"
                        : "border-[#202938] bg-[#121821] text-slate-400 hover:border-slate-600"
                    }`}
                  >
                    Confirmed (Close)
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmation("REJECTED")}
                    className={`border p-2.5 text-center font-semibold transition-all ${
                      confirmation === "REJECTED"
                        ? "border-rose-500 bg-rose-500/15 text-rose-400"
                        : "border-[#202938] bg-[#121821] text-slate-400 hover:border-slate-600"
                    }`}
                  >
                    Rejected (Reopen)
                  </button>
                </div>
              </div>

              {confirmation === "CONFIRMED" && (
                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                    Feedback Star Rating (1 to 5)
                  </label>
                  <div className="mt-1.5 flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setFeedbackRating(star)}
                        className={`flex h-8 w-8 items-center justify-center border ${
                          feedbackRating >= star
                            ? "border-amber-500/40 bg-amber-500/15 text-amber-400"
                            : "border-[#202938] bg-[#121821] text-slate-600"
                        }`}
                      >
                        <Star className="h-4 w-4 fill-current" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">
                  Customer Feedback / Verification Notes
                </label>
                <textarea
                  rows={2}
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="e.g. Customer tested speeds and confirmed stable connectivity."
                  className="mt-1 w-full border border-[#202938] bg-[#121821] p-2 text-xs text-[#F8FAFC] focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-[#202938] pt-4">
                <button
                  type="button"
                  onClick={() => setIsCloseOpen(false)}
                  className="border border-[#202938] px-4 py-2 text-xs text-[#94A3B8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="border border-purple-500 bg-purple-600 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-500 disabled:opacity-50"
                >
                  {submitting ? "Processing..." : confirmation === "CONFIRMED" ? "Close Ticket" : "Reopen to In Progress"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}