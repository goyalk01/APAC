"use client";

import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";

type Action = { tool: string; result: unknown };

type WorkflowResponse = {
  summary: string;
  actions: Action[];
  recommendations: string[];
};

export default function Page() {
  const [token, setToken] = useState<string>("");
  const [message, setMessage] = useState<string>("Schedule meeting tomorrow and create notes");
  const [result, setResult] = useState<WorkflowResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const apiBase = useMemo(() => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080", []);

  async function login() {
    const res = await fetch(`${apiBase}/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "demo-user", email: "demo@example.com", role: "user" }),
    });
    const data = await res.json();
    setToken(data.access_token);
  }

  async function runWorkflow() {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/v1/workflows/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message }),
      });
      const data = (await res.json()) as WorkflowResponse;
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <h1>Multi-Agent Productivity Assistant</h1>
        <p>Vertex function-calling orchestrator + MCP tool execution + Firestore memory</p>
        <div className="row">
          <button onClick={login}>Get Token</button>
          <button onClick={runWorkflow} disabled={!token || loading}>{loading ? "Running..." : "Execute Workflow"}</button>
        </div>
        <textarea
          aria-label="Workflow request"
          value={message}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setMessage(e.target.value)}
          rows={4}
          placeholder="Ask the assistant to plan tasks, schedule events, and draft notes"
        />
      </section>

      <section className="panel">
        <h2>Result</h2>
        {!result && <p>No workflow executed yet.</p>}
        {result && (
          <>
            <p><strong>Summary:</strong> {result.summary}</p>
            <h3>Actions</h3>
            <pre>{JSON.stringify(result.actions, null, 2)}</pre>
            <h3>Recommendations</h3>
            <ul>
              {result.recommendations.map((r: string) => <li key={r}>{r}</li>)}
            </ul>
          </>
        )}
      </section>
    </main>
  );
}
