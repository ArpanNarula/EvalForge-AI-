const PROD_API_BASE = "https://evalforge-ai-api.vercel.app";
const BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? PROD_API_BASE
    : "http://localhost:8000");

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(`${BASE}${path}`, opts);
  } catch (error) {
    throw new Error(`Network error while calling ${path}: ${error.message}`);
  }

  const contentType = res.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await res.json().catch(() => ({}))
    : await res.text().catch(() => "");

  if (!res.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      (typeof payload === "string" && payload.trim()) ||
      `HTTP ${res.status} from ${path}`;
    throw new Error(message);
  }

  return payload;
}

export function generateResponses(prompt, strategies, versionTag) {
  return request("POST", "/generate/", {
    prompt,
    strategies: strategies || ["balanced", "concise", "detailed"],
    num_responses: strategies?.length || 3,
    version_tag: versionTag || null,
  });
}

export function evaluateResponses(sessionId, prompt, responses) {
  return request("POST", "/evaluate/", { session_id: sessionId, prompt, responses });
}

export function getScoringWeights() {
  return request("GET", "/evaluate/weights");
}

export function submitFeedback(
  sessionId,
  prompt,
  selectedResponseId,
  selectedResponseText,
  rating,
  comment,
  scoreBreakdown,
) {
  return request("POST", "/feedback/", {
    session_id: sessionId,
    prompt,
    selected_response_id: selectedResponseId,
    selected_response_text: selectedResponseText,
    rating,
    comment: comment || null,
    score_breakdown: scoreBreakdown || null,
  });
}

export function getFeedbackStats() {
  return request("GET", "/feedback/stats");
}

export function getHistory(page = 1, pageSize = 10, minScore, version) {
  const params = new URLSearchParams({ page, page_size: pageSize });
  if (minScore != null) params.set("min_score", minScore);
  if (version) params.set("version", version);
  return request("GET", `/history/?${params}`);
}

export function getMetrics() {
  return request("GET", "/history/metrics");
}

export function retrieveSimilar(query, topK = 3) {
  return request("POST", "/retrieve/", { query, top_k: topK });
}

export function getRagContext(query, topK = 3) {
  return request("GET", `/retrieve/context?query=${encodeURIComponent(query)}&top_k=${topK}`);
}

export function getRetrievalStats() {
  return request("GET", "/retrieve/stats");
}
