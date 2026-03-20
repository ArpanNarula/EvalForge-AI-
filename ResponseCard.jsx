"use client";

/**
 * EvalForge AI — components/ResponseCard.jsx
 * Displays a single generated response with its evaluation score breakdown.
 * Props:
 *   response   — GeneratedResponse object
 *   score      — ResponseScore object (null while evaluating)
 *   isBest     — boolean, highlights #1 ranked response
 *   onFeedback — (responseId, rating) => void
 */

import { useState } from "react";
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronUp } from "lucide-react";

const STRATEGY_COLORS = {
  balanced: "#3B82F6",
  concise:  "#10B981",
  detailed: "#F59E0B",
  creative: "#A78BFA",
  structured: "#06B6D4",
};

function ScoreBar({ value, color }) {
  return (
    <div className="score-bar-track">
      <div
        className="score-bar-fill"
        style={{ width: `${value}%`, background: color || scoreColor(value) }}
      />
    </div>
  );
}

function scoreColor(v) {
  if (v >= 80) return "#10B981";
  if (v >= 60) return "#3B82F6";
  if (v >= 40) return "#F59E0B";
  return "#EF4444";
}

export default function ResponseCard({ response, score, isBest, onFeedback }) {
  const [expanded, setExpanded] = useState(true);
  const [feedback, setFeedback] = useState(null);
  const color = STRATEGY_COLORS[response.strategy] || "#6B7280";

  const handleFeedback = (rating) => {
    if (!score) return;
    setFeedback(rating);
    onFeedback?.(response.id, rating, {
      rule_based_total: score.rule_based.total,
      embedding_score: score.embedding.normalized_score,
      llm_judge_avg: score.llm_judge.average,
    });
  };

  return (
    <div className={`response-card ${isBest ? "response-card--best" : ""}`}>
      {/* Header */}
      <div className="response-card__header">
        <span className="strategy-tag" style={{ background: color + "22", color, borderColor: color + "44" }}>
          {response.strategy_label}
        </span>
        <span className="response-meta">{response.word_count}w</span>

        {score && (
          <span className="final-score" style={{ color: scoreColor(score.final_score) }}>
            {score.final_score.toFixed(1)}
          </span>
        )}
        {isBest && <span className="best-badge">BEST</span>}
        {score && !isBest && <span className="rank-badge">#{score.rank}</span>}

        <button
          className="expand-btn"
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-label="Toggle response"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Response text */}
      {expanded && (
        <div className="response-text">{response.text}</div>
      )}

      {/* Score breakdown */}
      {score && expanded && (
        <div className="score-breakdown">
          <div className="score-breakdown__grid">
            {[
              { label: "Correctness", val: score.llm_judge.correctness, color: "#3B82F6" },
              { label: "Relevance",   val: score.llm_judge.relevance,   color: "#10B981" },
              { label: "Clarity",     val: score.llm_judge.clarity,     color: "#F59E0B" },
            ].map(({ label, val, color: c }) => (
              <div key={label} className="subscore-cell">
                <div className="subscore-label">{label}</div>
                <div className="subscore-value" style={{ color: c }}>{Math.round(val)}</div>
                <ScoreBar value={val} color={c} />
              </div>
            ))}
          </div>

          <div className="score-breakdown__meta">
            <span>Rule-based: <strong>{score.rule_based.total.toFixed(0)}</strong></span>
            <span>Embedding: <strong>{score.embedding.normalized_score.toFixed(0)}</strong></span>
            <span>LLM judge: <strong>{score.llm_judge.average.toFixed(0)}</strong></span>
          </div>

          {score.llm_judge.explanation && (
            <p className="judge-explanation">"{score.llm_judge.explanation}"</p>
          )}

          {/* Feedback controls */}
          <div className="feedback-row">
            <span className="feedback-label">Feedback:</span>
            <button
              className={`feedback-btn ${feedback === 1 ? "feedback-btn--up" : ""}`}
              type="button"
              aria-pressed={feedback === 1}
              onClick={() => handleFeedback(1)}
            >
              <ThumbsUp size={12} /> Good
            </button>
            <button
              className={`feedback-btn ${feedback === -1 ? "feedback-btn--down" : ""}`}
              type="button"
              aria-pressed={feedback === -1}
              onClick={() => handleFeedback(-1)}
            >
              <ThumbsDown size={12} /> Poor
            </button>
            {feedback !== null && (
              <span className="feedback-recorded">Recorded ✓</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
