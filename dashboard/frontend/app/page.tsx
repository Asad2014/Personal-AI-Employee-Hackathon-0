"use client";
import { useEffect, useState } from "react";
import Dashboard from "./Dashboard";

// ClientOnly wrapper — prevents SSR hydration mismatch
export default function Page() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return null;
  return <Dashboard />;
}
