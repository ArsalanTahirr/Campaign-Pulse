"use client";

/**
 * PermissionGate — conditionally renders children based on the current user's
 * role within the active workspace.
 *
 * Props:
 *   action  {string}    — one of the actions defined in PERMISSION_MATRIX.
 *                         If provided, renders children when the current role
 *                         is in the allowed set for that action.
 *   roles   {string[]}  — explicit list of role names that may see children.
 *                         Either `action` or `roles` must be provided.
 *   fallback {ReactNode} — rendered instead of null when access is denied
 *                         (e.g. a disabled button or an empty fragment).
 *
 * Examples:
 *   <PermissionGate action="invite_collaborator">
 *     <InviteButton />
 *   </PermissionGate>
 *
 *   <PermissionGate roles={["Owner", "Agency"]} fallback={<DisabledBtn />}>
 *     <DeleteButton />
 *   </PermissionGate>
 */

import { useWorkspace } from "@/contexts/WorkspaceContext";

// Must stay in sync with backend/app/dependencies/permissions.py
const PERMISSION_MATRIX = {
  create_campaign:       ["Owner", "Agency", "Marketing Manager"],
  edit_campaign:         ["Owner", "Agency", "Marketing Manager"],
  delete_campaign:       ["Owner", "Agency"],
  start_campaign:        ["Owner", "Agency", "Marketing Manager"],
  pause_campaign:        ["Owner", "Agency", "Marketing Manager"],
  stop_campaign:         ["Owner", "Agency", "Marketing Manager"],
  manage_sequence:       ["Owner", "Agency", "Marketing Manager"],
  import_leads:          ["Owner", "Agency", "Marketing Manager"],
  view_leads:            ["Owner", "Agency", "Marketing Manager", "Data Analyst"],
  view_analytics:        ["Owner", "Agency", "Marketing Manager", "Data Analyst"],
  invite_collaborator:   ["Owner", "Agency"],
  remove_collaborator:   ["Owner", "Agency"],
  change_role:           ["Owner", "Agency"],
  manage_leads:          ["Owner", "Agency", "Marketing Manager"],
  manage_email_accounts: ["Owner", "Agency", "Marketing Manager"],
  view_workspace:        ["Owner", "Agency", "Marketing Manager", "Data Analyst"],
  edit_workspace:        ["Owner"],
};

export default function PermissionGate({ action, roles, fallback = null, children }) {
  const { role, loading } = useWorkspace();

  // While loading: show fallback when provided so controls can stay visible (e.g. disabled).
  if (loading) return fallback != null ? fallback : null;
  if (!role) return fallback;

  let allowed;
  if (action) {
    allowed = PERMISSION_MATRIX[action] ?? [];
  } else if (roles) {
    allowed = roles;
  } else {
    return children;
  }

  return allowed.includes(role) ? children : fallback;
}
