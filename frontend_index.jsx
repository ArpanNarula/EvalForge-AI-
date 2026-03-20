/**
 * EvalForge AI — pages/index.jsx
 * Main dashboard page.
 * Wires together: prompt input → generation → evaluation → feedback → metrics.
 */

"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import ResponseCard from "./ResponseCard";
import MetricsDashboard from "./MetricsDashboard";
import {
  generateResponses,
  evaluateResponses,
  submitFeedback,
  getHistory,
} from "./frontend_api";

const TABS = ["forge", "history", "metrics"];

export default function EvalForgePage() {
  const [tab, setTab] = useState("forge");
  const [prompt, setPrompt] = useState("");
  const [versionTag, setVersionTag] = useState("v1");
  const [phase, setPhase] = useState("idle");
  const [session, setSession] = useState(null);     // { id, prompt, responses }
  const [evalResult, setEvalResult] = useState(null); // EvaluationResult
  const [log, setLog] = useState([]);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const addLog = useCallback((msg) => {
    const ts = new Date().toLocaleTimeString();
    setLog((prev) => [...prev.slice(-40), `[${ts}] ${msg}`]);
  }, []);

  // ── Main agentic pipeline ──────────────────────────────────────────────────
  const runPipeline = useCallback(async () => {
    if (!prompt.trim() || phase !== "idle") return;
    setError(null);
    setSession(null);
    setEvalResult(null);
    setLog([]);

    try {
      // STEP 1: Generate
      setPhase("generating");
      addLog("Sending prompt to generation engine...");
      const genResult = await generateResponses(prompt, ["balanced", "concise", "detailed"], versionTag);
      setSession(genResult);
      addLog(`Generated ${genResult.responses.length} responses. Session: ${genResult.session_id.slice(0, 8)}...`);
      if (genResult.rag_context_used) addLog(`RAG: injected ${genResult.similar_prompts_found} similar past session(s).`);

      // STEP 2: Evaluate
      setPhase("evaluating");
      addLog("Running evaluation engine (rule-based + embedding + LLM judge)...");
      const evalRes = await evaluateResponses(genResult.session_id, genResult.prompt, genResult.responses);
      setEvalResult(evalRes);
      addLog(`Evaluation complete. Best response #${evalRes.best_response_id + 1}`);

      setPhase("done");
      addLog("Pipeline complete. Submit feedback to improve future rankings.");
    } catch (err) {
      setError(err.message);
      setPhase("idle");
      addLog(`Error: ${err.message}`);
    }
  }, [prompt, versionTag, phase, addLog]);

  // ── Feedback handler ───────────────────────────────────────────────────────
  const handleFeedback = useCallback(async (responseId, rating, scoreBreakdown) => {
    if (!session || !evalResult) return;
    const resp = session.responses.find((r) => r.id === responseId);
    if (!resp) return;
    try {
      await submitFeedback(
        session.session_id,
        session.prompt,
        responseId,
        resp.text,
        rating,
        null,
        scoreBreakdown,
      );
      addLog(`Feedback (${rating > 0 ? "👍" : "👎"}) recorded for response #${responseId + 1}.`);
    } catch (err) {
      addLog(`Feedback error: ${err.message}`);
    }
  }, [session, evalResult, addLog]);

  // ── Load history on tab switch ─────────────────────────────────────────────
  useEffect(() => {
    if (tab === "history") {
      getHistory(1, 20).then((res) => setHistory(res.entries)).catch(() => {});
    }
  }, [tab]);

  const reset = () => { setPhase("idle"); setSession(null); setEvalResult(null); setLog([]); setError(null); setPrompt(""); };
  const isRunning = phase === "generating" || phase === "evaluating";

  const sortedScores = evalResult
    ? [...evalResult.scores].sort((a, b) => a.rank - b.rank)
    : [];

  return (
    <div className="page">
      {/* Header */}
      <header className="header">
        <div className="header__logo">⬡ EvalForge AI</div>
        <nav className="header__nav">
          {TABS.map((t) => (
            <button key={t} className={`tab-btn ${tab === t ? "tab-btn--active" : ""}`} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
        <div className={`status-indicator ${isRunning ? "status-indicator--running" : phase === "done" ? "status-indicator--done" : ""}`}>
          {isRunning ? "Running..." : phase === "done" ? "Complete" : "Ready"}
        </div>
      </header>

      <main className="main">
        {/* ── FORGE TAB ── */}
        {tab === "forge" && (
          <div className="forge-layout">
            <div className="forge-content">
              {/* Prompt input */}
              <section className="section">
                <div className="section__row">
                  <label className="field-label">Prompt</label>
                  <div className="version-tag-row">
                    <span className="field-label">Version</span>
                    <input
                      className="version-input"
                      value={versionTag}
                      onChange={(e) => setVersionTag(e.target.value)}
                      placeholder="v1"
                    />
                  </div>
                </div>
                <textarea
                  className="prompt-input"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Enter a prompt to evaluate across multiple response strategies..."
                  rows={4}
                  disabled={isRunning}
                />
                <div className="btn-row">
                  <button
                    className="btn btn--primary"
                    onClick={runPipeline}
                    disabled={!prompt.trim() || isRunning}
                  >
                    {isRunning ? "Running pipeline..." : "Run EvalForge"}
                  </button>
                  {phase !== "idle" && (
                    <button className="btn btn--ghost" onClick={reset}>Reset</button>
                  )}
                </div>
              </section>

              {/* Error */}
              {error && <div className="error-banner">Error: {error}</div>}

              {/* Pipeline log */}
              {log.length > 0 && (
                <section className="section">
                  <div className="field-label">Pipeline Log</div>
                  <div className="pipeline-log" ref={logRef}>
                    {log.map((l, i) => <div key={i}>{l}</div>)}
                    {isRunning && <div className="log-cursor">▌</div>}
                  </div>
                </section>
              )}

              {/* Responses */}
              {session?.responses?.length > 0 && (
                <section className="section">
                  <div className="field-label">
                    Responses
                    {evalResult && ` — ${evalResult.scores.length} evaluated`}
                  </div>
                  {session.responses.map((resp) => {
                    const score = evalResult?.scores.find((s) => s.response_id === resp.id);
                    const isBest = score?.rank === 1 && phase === "done";
                    return (
                      <ResponseCard
                        key={resp.id}
                        response={resp}
                        score={score}
                        isBest={isBest}
                        onFeedback={handleFeedback}
                      />
                    );
                  })}
                </section>
              )}

              {/* Empty state */}
              {!session && phase === "idle" && (
                <div className="empty-state">
                  <div className="empty-state__icon">⬡</div>
                  <p>Run a prompt through the EvalForge pipeline to see multi-strategy responses with ranked scores.</p>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <aside className="sidebar">
              <div className="field-label" style={{ marginBottom: 10 }}>Ranking</div>
              {sortedScores.length > 0 ? (
                sortedScores.map((sc) => {
                  const resp = session?.responses.find((r) => r.id === sc.response_id);
                  return (
                    <div key={sc.response_id} className="rank-item">
                      <span className={`rank-badge rank-badge--${sc.rank}`}>#{sc.rank}</span>
                      <span className="rank-label">{resp?.strategy_label}</span>
                      <span className="rank-score">{sc.final_score.toFixed(0)}</span>
                    </div>
                  );
                })
              ) : (
                <p className="sidebar-empty">Run pipeline to see rankings.</p>
              )}

              <div className="field-label" style={{ marginTop: 20, marginBottom: 8 }}>Quick Prompts</div>
              {[
                "Explain how attention mechanisms work in transformers",
                "What are the tradeoffs between SQL and NoSQL?",
                "How does backpropagation update neural network weights?",
                "Compare REST vs GraphQL for API design",
              ].map((qp) => (
                <button
                  key={qp}
                  className="quick-prompt-btn"
                  onClick={() => { setPrompt(qp); }}
                  disabled={isRunning}
                >
                  {qp}
                </button>
              ))}
            </aside>
          </div>
        )}

        {/* ── HISTORY TAB ── */}
        {tab === "history" && (
          <div className="history-panel">
            <h2 className="panel-title">Session History</h2>
            {history.length === 0 ? (
              <p className="empty-text">No sessions yet. Run the pipeline first.</p>
            ) : (
              history.map((entry) => (
                <div key={entry.session_id} className="history-card">
                  <div className="history-card__row">
                    <span className="history-tag">{entry.prompt_version}</span>
                    <span className="history-score">{entry.best_score.toFixed(1)}</span>
                    {entry.feedback_rating != null && (
                      <span>{entry.feedback_rating > 0 ? "👍" : "👎"}</span>
                    )}
                    <span className="history-time">
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="history-prompt">{entry.prompt}</p>
                  <p className="history-response">{entry.best_response_text.slice(0, 200)}...</p>
                </div>
              ))
            )}
          </div>
        )}

        {/* ── METRICS TAB ── */}
        {tab === "metrics" && <MetricsDashboard />}
      </main>
    </div>
  );
}
