"use client";

import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import ReactFlow, { Background, Controls, Edge, MarkerType, Node } from "reactflow";
import "reactflow/dist/style.css";

type Action = { tool: string; result: unknown };

type WorkflowResponse = {
  summary: string;
  story: string;
  timeline: Array<{ step: number; node: string; action: string }>;
  actions: Action[];
  recommendations: string[];
  message: string;
  confidence_score: number;
};

type TaskItem = { task_id: string; title: string };
type EventItem = { event_id: string; title: string };
type DependencyItem = { parent_id: string; child_id: string; type: string };
type CascadeStreamEvent = { node_id?: string; status: string; cascade_id?: string; reason?: string; summary?: string };

export default function Page() {
  const [token, setToken] = useState<string>("");
  const [message, setMessage] = useState<string>("Schedule meeting tomorrow and create notes");
  const [result, setResult] = useState<WorkflowResponse | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [dependencies, setDependencies] = useState<DependencyItem[]>([]);
  const [updatedNodeIds, setUpdatedNodeIds] = useState<string[]>([]);
  const [streamStatus, setStreamStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const apiBase = useMemo(() => process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080", []);

  const graphNodes: Node[] = useMemo(() => {
    const eventNodes: Node[] = events.map((item, idx) => ({
      id: item.event_id,
      data: { label: item.title || item.event_id },
      position: { x: 80 + (idx % 3) * 260, y: 80 + Math.floor(idx / 3) * 160 },
      style: {
        background: updatedNodeIds.includes(item.event_id) ? "#fde68a" : "#bfdbfe",
        borderRadius: 18,
        border: "1px solid #1d4ed8",
        padding: 10,
        minWidth: 180,
      },
      className: updatedNodeIds.includes(item.event_id) ? "node-pulse" : "",
    }));

    const taskNodes: Node[] = tasks.map((item, idx) => ({
      id: item.task_id,
      data: { label: item.title || item.task_id },
      position: { x: 120 + (idx % 3) * 260, y: 380 + Math.floor(idx / 3) * 130 },
      style: {
        background: updatedNodeIds.includes(item.task_id) ? "#fde68a" : "#bbf7d0",
        borderRadius: 8,
        border: "1px solid #166534",
        padding: 10,
        minWidth: 180,
      },
      className: updatedNodeIds.includes(item.task_id) ? "node-pulse" : "",
    }));

    return [...eventNodes, ...taskNodes];
  }, [tasks, events, updatedNodeIds]);

  const graphEdges: Edge[] = useMemo(
    () =>
      dependencies.map((dep) => ({
        id: `${dep.parent_id}->${dep.child_id}`,
        source: dep.parent_id,
        target: dep.child_id,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        label: dep.type,
      })),
    [dependencies]
  );

  async function login() {
    const res = await fetch(`${apiBase}/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "demo-user", email: "demo@example.com", role: "user" }),
    });
    const data = await res.json();
    setToken(data.access_token);
  }

  async function refreshGraphData(accessToken: string) {
    const headers = { Authorization: `Bearer ${accessToken}` };
    const [tasksRes, eventsRes, depsRes] = await Promise.all([
      fetch(`${apiBase}/v1/me/tasks`, { headers }),
      fetch(`${apiBase}/v1/me/events`, { headers }),
      fetch(`${apiBase}/v1/dependencies`, { headers }),
    ]);
    const tasksData = await tasksRes.json();
    const eventsData = await eventsRes.json();
    const depsData = await depsRes.json();
    setTasks(tasksData.items ?? []);
    setEvents(eventsData.items ?? []);
    setDependencies(depsData ?? []);
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
      await refreshGraphData(token);

      if (data.timeline?.length) {
        data.timeline.forEach((entry) => {
          setTimeout(() => {
            if (!entry.node) {
              return;
            }
            setUpdatedNodeIds((prev) => Array.from(new Set([...prev, entry.node])));
            setTimeout(() => {
              setUpdatedNodeIds((prev) => prev.filter((id) => id !== entry.node));
            }, 1000);
          }, Math.max(1, entry.step) * 400);
        });
      }
    } finally {
      setLoading(false);
    }
  }

  async function startCascadeStream() {
    if (!token || events.length === 0) {
      return;
    }
    const baseNode = events[0].event_id;
    const source = new EventSource(
      `${apiBase}/v1/workflows/stream?node_id=${encodeURIComponent(baseNode)}&change_type=time_updated&access_token=${encodeURIComponent(
        token
      )}&payload_json=${encodeURIComponent(JSON.stringify({ old_start_time: "10:00", new_start_time: "15:00" }))}`
    );

    source.addEventListener("update", (event) => {
      const parsed = JSON.parse((event as MessageEvent).data) as CascadeStreamEvent;
      if (parsed.node_id) {
        setUpdatedNodeIds((prev) => Array.from(new Set([...prev, parsed.node_id as string])));
        setTimeout(() => {
          setUpdatedNodeIds((prev) => prev.filter((id) => id !== parsed.node_id));
        }, 1800);
      }
      setStreamStatus(parsed.summary ?? parsed.status);
      if (parsed.status === "complete") {
        source.close();
      }
    });
  }

  useEffect(() => {
    if (!token) return;
    void refreshGraphData(token);
  }, [token]);

  return (
    <main className="shell">
      <section className="panel">
        <h1>CASCADE Ripple Workflow Engine</h1>
        <p>Visual DAG + real-time stream + adaptive cascade decisions</p>
        <div className="row">
          <button onClick={login}>Get Token</button>
          <button onClick={runWorkflow} disabled={!token || loading}>{loading ? "Running..." : "Execute Workflow"}</button>
          <button onClick={startCascadeStream} disabled={!token || events.length === 0}>Stream Cascade</button>
        </div>
        <textarea
          aria-label="Workflow request"
          value={message}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setMessage(e.target.value)}
          rows={4}
          placeholder="Ask the assistant to plan tasks, schedule events, and draft notes"
        />
        <p><strong>Stream:</strong> {streamStatus || "idle"}</p>
      </section>

      <section className="panel">
        <h2>Result</h2>
        {!result && <p>No workflow executed yet.</p>}
        {result && (
          <>
            <p><strong>Summary:</strong> {result.summary}</p>
            <p><strong>Story:</strong> {result.story}</p>
            <p><strong>Message:</strong> {result.message}</p>
            <p><strong>Confidence:</strong> {result.confidence_score}</p>
            <h3>Timeline</h3>
            <pre>{JSON.stringify(result.timeline, null, 2)}</pre>
            <h3>Actions</h3>
            <pre>{JSON.stringify(result.actions, null, 2)}</pre>
            <h3>Recommendations</h3>
            <ul>
              {result.recommendations.map((r: string) => <li key={r}>{r}</li>)}
            </ul>
          </>
        )}
      </section>

      <section className="panel graph-panel">
        <h2>Dependency Graph</h2>
        <div className="graph-wrap">
          <ReactFlow nodes={graphNodes} edges={graphEdges} fitView>
            <Background />
            <Controls />
          </ReactFlow>
        </div>
      </section>
    </main>
  );
}
