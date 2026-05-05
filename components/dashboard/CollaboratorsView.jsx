"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2,
  Mail,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import PermissionGate from "@/components/ui/PermissionGate";
import { messageFromApiErrorBody } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const roleColors = {
  Owner:               "bg-indigo-50 text-indigo-600 border border-indigo-100",
  Agency:              "bg-indigo-50 text-indigo-600 border border-indigo-100",
  "Marketing Manager": "bg-indigo-50 text-indigo-600 border border-indigo-100",
  "Data Analyst":      "bg-indigo-50 text-indigo-600 border border-indigo-100",
};

const statusBadge = {
  pending:   "bg-amber-50 text-amber-600 border border-amber-100",
  accepted:  "bg-emerald-50 text-emerald-600 border border-emerald-100",
  declined:  "bg-rose-50 text-rose-500 border border-rose-100",
  cancelled: "bg-slate-100 text-slate-500 border border-slate-200",
  expired:   "bg-slate-100 text-slate-500 border border-slate-200",
};

// ---------------------------------------------------------------------------
// Invite Modal
// ---------------------------------------------------------------------------

function InviteModal({ workspaceId, onInvited, onClose }) {
  const [email, setEmail] = useState("");
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [rolesLoading, setRolesLoading] = useState(true);

  useEffect(() => {
    async function loadRoles() {
      setRolesLoading(true);
      try {
        const res = await fetch(`${API}/workspaces/${workspaceId}/invitations/roles`, {
          credentials: "include",
        });
        if (res.ok) {
          const list = await res.json();
          if (list.length > 0) {
            setRoles(list);
            setSelectedRole(list[0]);
          } else {
            setRoles([]);
            setSelectedRole(null);
          }
        } else {
          const err = await res.json().catch(() => ({}));
          throw new Error(messageFromApiErrorBody(err, "Failed to load roles."));
        }
      } catch (err) {
        setRoles([]);
        setSelectedRole(null);
        toast.error(err.message || "Failed to load roles.");
      } finally {
        setRolesLoading(false);
      }
    }
    loadRoles();
  }, [workspaceId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || !selectedRole) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/workspaces/${workspaceId}/invitations`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invitee_email: email.trim(), role_id: selectedRole.role_id }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to send invitation."));
      }
      const inv = await res.json();
      toast.success(`Invitation sent to ${inv.invitee_email}`);
      onInvited(inv);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Invite a teammate
          </h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Email address</label>
            <input
              autoFocus
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@example.com"
              className="h-10 w-full rounded-xl border border-slate-200/60 bg-slate-50/50 px-3 text-sm text-slate-700 outline-none transition-all duration-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
              required
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Role</label>
            {rolesLoading ? (
              <p className="text-xs text-slate-400">Loading roles...</p>
            ) : roles.length === 0 ? (
              <p className="text-xs text-rose-500">No invitable roles available.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {roles.map((r) => (
                  <button
                    key={r.role_id}
                    type="button"
                    onClick={() => setSelectedRole(r)}
                    className={[
                      "rounded-full px-3 py-1 text-xs font-semibold transition-all",
                      selectedRole?.role_id === r.role_id
                        ? "ring-2 ring-blue-500 ring-offset-1 " + (roleColors[r.name] || "bg-slate-100 text-slate-700")
                        : (roleColors[r.name] || "bg-slate-100 text-slate-700") + " opacity-60 hover:opacity-100",
                    ].join(" ")}
                  >
                    {r.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !email.trim() || !selectedRole}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:bg-indigo-500 active:scale-95 disabled:opacity-60"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Send Invite
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CollaboratorsView() {
  const { workspace } = useWorkspace();
  const [collaborators, setCollaborators] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [cancelingId, setCancelingId] = useState(null);
  const [removingId, setRemovingId] = useState(null);
  const [tab, setTab] = useState("members");

  const fetchData = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const [collabRes, invRes] = await Promise.all([
        fetch(`${API}/workspaces/${workspace.workspace_id}/collaborators`, { credentials: "include" }),
        fetch(`${API}/workspaces/${workspace.workspace_id}/invitations`, { credentials: "include" }),
      ]);
      if (collabRes.ok) {
        const data = await collabRes.json();
        setCollaborators(data);
      }
      if (invRes.ok) setInvitations(await invRes.json());
    } catch {
      toast.error("Failed to load collaborators.");
    } finally {
      setLoading(false);
    }
  }, [workspace]);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function cancelInvitation(invId) {
    setCancelingId(invId);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspace.workspace_id}/invitations/${invId}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to cancel invitation."));
      }
      toast.success("Invitation cancelled.");
      setInvitations((prev) => prev.filter((i) => i.invitation_id !== invId));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCancelingId(null);
    }
  }

  async function removeCollaborator(collabId) {
    setRemovingId(collabId);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspace.workspace_id}/collaborators/${collabId}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to remove collaborator."));
      }
      toast.success("Collaborator removed.");
      setCollaborators((prev) => prev.filter((c) => c.collaborator_id !== collabId));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRemovingId(null);
    }
  }

  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  return (
    <section className="flex flex-1 flex-col gap-6 bg-slate-50 px-6 py-6 sm:px-8">
      {showInviteModal && workspace && (
        <InviteModal
          workspaceId={workspace.workspace_id}
          onInvited={(inv) => {
            setInvitations((prev) => [inv, ...prev]);
            setShowInviteModal(false);
            setTab("invitations");
          }}
          onClose={() => setShowInviteModal(false)}
        />
      )}

      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black tracking-tight text-slate-900">Team</h1>
        <PermissionGate action="invite_collaborator">
          <button
            type="button"
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:bg-indigo-500 active:scale-95"
          >
            <UserPlus className="mr-2 h-4 w-4" />
            Invite Member
          </button>
        </PermissionGate>
      </div>

      {/* Segmented tab control */}
      <div className="flex items-center border-b border-slate-200/60">
        <div className="relative flex gap-1 rounded-2xl border border-slate-200/50 bg-slate-100/50 p-1">
          {["members", "invitations"].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className="relative z-10 px-6 py-2 text-sm font-medium capitalize transition-colors"
            >
              {tab === t && (
                <motion.span
                  layoutId="activeTab"
                  className="absolute inset-0 rounded-xl bg-white shadow-sm"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              <span className={[
                "relative z-10 font-bold",
                tab === t ? "text-indigo-600" : "text-slate-500 hover:text-slate-700"
              ].join(" ")}>
                {t}
                {t === "invitations" && pendingInvitations.length > 0 && (
                  <span className="ml-1.5 rounded-full bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold text-white">
                    {pendingInvitations.length}
                  </span>
                )}
              </span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      ) : tab === "members" ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200/60 bg-white shadow-sm">
          {collaborators.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-500">No members yet.</p>
          ) : (
            <div>
              <div className="grid grid-cols-[1fr_140px_130px_52px] items-center gap-4 border-b border-slate-100 px-5 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                <div>Member</div>
                <div>Role</div>
                <div>Status</div>
                <div />
              </div>
              {collaborators.map((collab, i) => {
                const roleName = collab.role?.name || collab.roles?.[0]?.name || "—";
                return (
                  <motion.div
                    key={collab.collaborator_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.22, delay: i * 0.05, ease: "easeOut" }}
                    className="grid grid-cols-[1fr_140px_130px_52px] items-center gap-4 border-b border-slate-100 px-5 py-4 last:border-0 transition-colors hover:bg-slate-50/80"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-black text-indigo-600">
                        {(collab.full_name || collab.email || "?")[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-900">
                          {collab.full_name || "(No name)"}
                        </p>
                        <p className="text-xs text-slate-500">{collab.email}</p>
                      </div>
                    </div>

                    <div>
                      <span className={["inline-flex h-6 min-w-[90px] items-center justify-center rounded-lg px-3 text-xs font-bold uppercase", roleColors[roleName] || "bg-indigo-50 text-indigo-600 border border-indigo-100"].join(" ")}>
                        {roleName}
                      </span>
                    </div>

                    <div>
                      <span className={["inline-flex h-6 min-w-[90px] items-center justify-center rounded-full px-3 text-xs font-bold", statusBadge[collab.invite_status] || "bg-slate-100 text-slate-500 border border-slate-200"].join(" ")}>
                        {collab.invite_status}
                      </span>
                    </div>

                    <div className="flex justify-end">
                      <PermissionGate action="remove_collaborator">
                        <button
                          type="button"
                          disabled={removingId === collab.collaborator_id}
                          onClick={() => removeCollaborator(collab.collaborator_id)}
                          className="rounded-lg p-1.5 transition-colors hover:bg-rose-50 disabled:opacity-40"
                          aria-label="Remove collaborator"
                        >
                          {removingId === collab.collaborator_id
                            ? <Loader2 className="h-4 w-4 animate-spin text-rose-400" />
                            : <Trash2 className="h-4 w-4 text-slate-300 hover:text-rose-500 transition-colors" />}
                        </button>
                      </PermissionGate>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200/60 bg-white shadow-sm">
          {invitations.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-500">No invitations sent yet.</p>
          ) : (
            <div>
              <div className="grid grid-cols-[1fr_130px_140px_60px] items-center border-b border-slate-100 px-5 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                <div>Email</div>
                <div>Status</div>
                <div>Expires</div>
                <div />
              </div>
              {invitations.map((inv, i) => (
                <motion.div
                  key={inv.invitation_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.22, delay: i * 0.05, ease: "easeOut" }}
                  className="grid grid-cols-[1fr_130px_140px_60px] items-center border-b border-slate-100 px-5 py-4 last:border-0 transition-colors hover:bg-slate-50/80"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100">
                      <Mail className="h-3.5 w-3.5 text-slate-400" />
                    </div>
                    <span className="text-sm font-bold text-slate-900">{inv.invitee_email}</span>
                  </div>
                  <div>
                    <span className={["rounded-full px-3 py-0.5 text-[10px] font-black", statusBadge[inv.status] || "bg-slate-100 text-slate-500 border border-slate-200"].join(" ")}>
                      {inv.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">
                    {new Date(inv.expires_at).toLocaleDateString()}
                  </div>
                  <div className="flex justify-end">
                    {inv.status === "pending" && (
                      <PermissionGate action="invite_collaborator">
                        <button
                          type="button"
                          disabled={cancelingId === inv.invitation_id}
                          onClick={() => cancelInvitation(inv.invitation_id)}
                          className="rounded-lg p-1.5 transition-colors hover:bg-rose-50 disabled:opacity-40"
                          aria-label="Cancel invitation"
                        >
                          {cancelingId === inv.invitation_id
                            ? <Loader2 className="h-4 w-4 animate-spin text-rose-400" />
                            : <X className="h-4 w-4 text-slate-300 hover:text-rose-500 transition-colors" />}
                        </button>
                      </PermissionGate>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
