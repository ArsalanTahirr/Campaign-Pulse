"use client";

import { useCallback, useEffect, useState } from "react";
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
  Owner:              "bg-violet-100 text-violet-700",
  Agency:             "bg-blue-100 text-blue-700",
  "Marketing Manager":"bg-emerald-100 text-emerald-700",
  "Data Analyst":     "bg-amber-100 text-amber-700",
};

const statusBadge = {
  pending:   "bg-amber-100 text-amber-700",
  accepted:  "bg-emerald-100 text-emerald-700",
  declined:  "bg-rose-100 text-rose-700",
  cancelled: "bg-slate-100 text-slate-500",
  expired:   "bg-slate-100 text-slate-500",
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
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400"
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
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
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
    <section className="flex flex-1 flex-col gap-6 bg-slate-50/60 px-6 py-6 sm:px-8">
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

      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
          {["members", "invitations"].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={[
                "rounded-lg px-4 py-1.5 text-sm font-semibold capitalize transition-colors",
                tab === t
                  ? "bg-white text-slate-800 shadow-sm dark:bg-slate-700 dark:text-slate-100"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200",
              ].join(" ")}
            >
              {t}
              {t === "invitations" && pendingInvitations.length > 0 && (
                <span className="ml-1.5 rounded-full bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {pendingInvitations.length}
                </span>
              )}
            </button>
          ))}
        </div>

        <PermissionGate action="invite_collaborator">
          <button
            type="button"
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-700"
          >
            <UserPlus className="h-4 w-4" />
            Invite Member
          </button>
        </PermissionGate>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : tab === "members" ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {collaborators.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-500">No members yet.</p>
          ) : (
            <div>
              <div className="grid grid-cols-[1fr_160px_120px_60px] items-center border-b border-slate-100 px-5 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <div>Member</div>
                <div>Role</div>
                <div>Status</div>
                <div />
              </div>
              {collaborators.map((collab) => {
                // Backward-compatible: support both legacy `roles[]` and new `role`.
                const roleName = collab.role?.name || collab.roles?.[0]?.name || "—";
                return (
                  <div
                    key={collab.collaborator_id}
                    className="grid grid-cols-[1fr_160px_120px_60px] items-center border-b border-slate-50 px-5 py-4 last:border-0 dark:border-slate-800"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        {collab.full_name || "(No name)"}
                      </p>
                      <p className="text-xs text-slate-500">{collab.email}</p>
                    </div>

                    <span className={["inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", roleColors[roleName] || "bg-slate-100 text-slate-700"].join(" ")}>
                      {roleName}
                    </span>

                    <div>
                      <span className={["rounded-full px-2.5 py-1 text-xs font-semibold", statusBadge[collab.invite_status] || "bg-slate-100 text-slate-500"].join(" ")}>
                        {collab.invite_status}
                      </span>
                    </div>

                    <div className="flex justify-end">
                      <PermissionGate action="remove_collaborator">
                        <button
                          type="button"
                          disabled={removingId === collab.collaborator_id}
                          onClick={() => removeCollaborator(collab.collaborator_id)}
                          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-500 disabled:opacity-40"
                          aria-label="Remove collaborator"
                        >
                          {removingId === collab.collaborator_id
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <Trash2 className="h-4 w-4" />}
                        </button>
                      </PermissionGate>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {invitations.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-500">No invitations sent yet.</p>
          ) : (
            <div>
              <div className="grid grid-cols-[1fr_120px_140px_80px] items-center border-b border-slate-100 px-5 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <div>Email</div>
                <div>Status</div>
                <div>Expires</div>
                <div />
              </div>
              {invitations.map((inv) => (
                <div
                  key={inv.invitation_id}
                  className="grid grid-cols-[1fr_120px_140px_80px] items-center border-b border-slate-50 px-5 py-4 last:border-0 dark:border-slate-800"
                >
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 shrink-0 text-slate-400" />
                    <span className="text-sm text-slate-700 dark:text-slate-300">{inv.invitee_email}</span>
                  </div>
                  <div>
                    <span className={["rounded-full px-2.5 py-1 text-xs font-semibold", statusBadge[inv.status] || "bg-slate-100 text-slate-500"].join(" ")}>
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
                          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-500 disabled:opacity-40"
                          aria-label="Cancel invitation"
                        >
                          {cancelingId === inv.invitation_id
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <X className="h-4 w-4" />}
                        </button>
                      </PermissionGate>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
