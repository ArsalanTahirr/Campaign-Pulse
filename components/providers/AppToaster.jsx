"use client";

import { Toaster } from "sonner";
import { useTheme } from "next-themes";

export default function AppToaster() {
  const { resolvedTheme } = useTheme();

  return (
    <Toaster
      position="top-center"
      richColors
      duration={2000}
      theme={resolvedTheme === "dark" ? "dark" : "light"}
      toastOptions={{
        className: "backdrop-blur-md",
      }}
    />
  );
}
