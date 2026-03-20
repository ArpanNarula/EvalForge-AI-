"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getFeedbackStats, getMetrics } from "../services/api";

const DEFAULT_WEIGHTS = { rule_based: 0.20, embedding: 0.30, llm_judge: 0.50 };
const WEIGHT_COLORS = { rule_based: "#A78BFA", embedding: "#06B6D4", llm_judge: "#F59E0B" };
const WEIGHT_LABELS = { rule_based: "Rule-Based", embedding: "Embedding Sim.", llm_judge: "LLM Judge" };

function WeightBar({ method, current, defaultVal }) {
  const drift = current - defaultVal;
  const color = WEIGHT_COLORS[method];
  return (
    <div className="weight-row">
      <div className="weight-row__label">
        <span>{WEIGHT_LABELS[method]}</span>
        <span style={{ fontFamily: "monospace", color }}>{(current * 100).toFixed(1)}%</span>
      </div>
      <div className="weight-track">
        <div className="weight-bar" style={{ width: `${current * 100}%`, background: color }} />
        <div
          className="weight-default-marker"
          style={{ left: `${defaultVal * 100}%` }}
          title={`Default: ${(defaultVal * 100).toFixed(0)}%`}
        />
      </div>
      <span className={`weight-drift ${drift > 0 ? "drift-up" : drift < 0 ? "drift-down" : ""}`}>
        {drift === 0 ? "—" : `${drift > 0 ? "+" : ""}${(drift * 100).toFixed(1)}%`}
      </span>
    </div>
  );
}

export default function MetricsDashboard() {
  const [stats, setStats] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getFeedbackStats(), getMetrics()])
      .then(([s, m]) => { setStats(s); setMetrics(m); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="metrics-loading">Loading metrics...</div>;
  if (error) return <div className="metrics-error">Error: {error}</div>;
  if (!stats) return null;

  const weights = stats.current_weights || DEFAULT_WEIGHTS;
  const distData = metrics?.score_distribution
    ? Object.entries(metrics.score_distribution).map(([range, count]) => ({ range, count }))
    : [];

  return (
    <div className="metrics-dashboard">
      <h2 className="metrics-title">Evaluation Metrics</h2>

      <div className="kpi-row">
        {[
          { label: "Sessions", val: metrics?.total_sessions ?? "—" },
          { label: "Avg Best Score", val: metrics?.avg_best_score ?? "—" },
          { label: "Feedback", val: stats.total_feedback },
          { label: "Positive Rate", val: `${((stats.positive_rate || 0) * 100).toFixed(0)}%` },
        ].map(({ label, val }) => (
          <div key={label} className="kpi-card">
            <div className="kpi-label">{label}</div>
            <div className="kpi-value">{val}</div>
          </div>
        ))}
      </div>

      <div className="metrics-section">
        <h3 className="metrics-section-title">
          Scoring Weight Drift
          <span className="section-subtitle">White marker = default | Bar = current</span>
        </h3>
        {Object.keys(DEFAULT_WEIGHTS).map((method) => (
          <WeightBar
            key={method}
            method={method}
            current={weights[method] ?? DEFAULT_WEIGHTS[method]}
            defaultVal={DEFAULT_WEIGHTS[method]}
          />
        ))}
      </div>

      {distData.length > 0 && (
        <div className="metrics-section">
          <h3 className="metrics-section-title">Score Distribution</h3>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={distData} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
              <XAxis dataKey="range" tick={{ fontSize: 11, fill: "#6B7280" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} />
              <Tooltip
                contentStyle={{ background: "#0F172A", border: "1px solid #1E2A3A", borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: "#E5E7EB" }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {distData.map((entry, i) => (
                  <Cell key={i} fill={["#EF4444", "#F59E0B", "#3B82F6", "#10B981"][i] || "#6B7280"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {metrics?.prompt_versions && Object.keys(metrics.prompt_versions).length > 0 && (
        <div className="metrics-section">
          <h3 className="metrics-section-title">Prompt Versions</h3>
          <table className="version-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Sessions</th>
                <th>Avg Score</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.prompt_versions).map(([ver, data]) => (
                <tr key={ver}>
                  <td><code>{ver}</code></td>
                  <td>{data.count}</td>
                  <td style={{ color: data.avg_score >= 70 ? "#10B981" : "#F59E0B" }}>
                    {data.avg_score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="consistency-note">
        <strong>Annotator Consistency:</strong> Feedback agreement rate is tracked per session.
        When the same prompt is submitted multiple times and receives conflicting ratings,
        it flags inconsistency. Track via <code>GET /feedback/stats</code>.
      </div>
    </div>
  );
}
