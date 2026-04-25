"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MainLayout from "@/components/dashboard/MainLayout";

export default function DashboardPage() {
  const router = useRouter();
  const [checkedAuth, setCheckedAuth] = useState(false);
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    async function verifySession() {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          method: "GET",
          credentials: "include",
        });
        if (!response.ok) {
          router.replace("/login");
          return;
        }
        setCheckedAuth(true);
      } catch {
        router.replace("/login");
      }
    }
    verifySession();
  }, [API_BASE_URL, router]);

  if (!checkedAuth) return null;
  return <MainLayout />;
}
