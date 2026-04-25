"use client";

/**
 * WorkspaceContext — provides the current workspace and the authenticated
 * user's role within it to every component in the dashboard tree.
 *
 * Usage:
 *   const { workspace, role, workspaces, switchWorkspace, loading } = useWorkspace();
 *
 * Wrap the dashboard layout with <WorkspaceProvider> and read via useWorkspace().
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [workspace, setWorkspace] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchWorkspaces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/workspaces`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to load workspaces.");
      const data = await res.json();
      setWorkspaces(data);
      if (data.length > 0 && !workspace) {
        const stored = typeof window !== "undefined"
          ? window.localStorage.getItem("cp_workspace_id")
          : null;
        const found = stored ? data.find((w) => w.workspace_id === stored) : null;
        setWorkspace(found || data[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  // workspace intentionally excluded — only run on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  // Fetch the current user's role in the active workspace
  useEffect(() => {
    if (!workspace) return;
    let active = true;

    async function fetchRole() {
      try {
        const res = await fetch(
          `${API}/workspaces/${workspace.workspace_id}/collaborators`,
          { credentials: "include" }
        );
        if (!res.ok) return;
        const collabs = await res.json();
        // Find the current user via /auth/me
        const meRes = await fetch(`${API}/auth/me`, { credentials: "include" });
        if (!meRes.ok) return;
        const me = await meRes.json();
        const mine = collabs.find((c) => c.user_id === me.user_id);
        if (active && mine?.roles?.length > 0) {
          setRole(mine.roles[0].name);
        }
      } catch {
        // Non-fatal — role stays null
      }
    }

    fetchRole();
    return () => { active = false; };
  }, [workspace]);

  const switchWorkspace = useCallback((ws) => {
    setWorkspace(ws);
    setRole(null);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("cp_workspace_id", ws.workspace_id);
    }
  }, []);

  const createWorkspace = useCallback(async (name) => {
    const res = await fetch(`${API}/workspaces`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create workspace.");
    }
    const created = await res.json();
    setWorkspaces((prev) => [...prev, created]);
    switchWorkspace(created);
    return created;
  }, [switchWorkspace]);

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        workspaces,
        role,
        loading,
        error,
        switchWorkspace,
        createWorkspace,
        refetch: fetchWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used inside <WorkspaceProvider>.");
  }
  return ctx;
}
