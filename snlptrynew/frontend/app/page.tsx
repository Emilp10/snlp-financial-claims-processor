"use client"

import { useCallback, useState } from "react"
import type { ChangeEvent, FormEvent } from "react"

interface EvidenceChunk {
  text: string
  source: string
  score: number
  chunk_index?: number | null
}

interface VerdictResult {
  verdict: string
  confidence: number
  reasoning: string
  citations: string[]
}

interface ClaimResponse {
  claim: string
  result: VerdictResult
  evidence: EvidenceChunk[]
}

interface ChatResult {
  answer: string
  citations: string[]
}

interface ChatResponse {
  session_id: string
  result: ChatResult
  evidence: EvidenceChunk[]
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000"

async function postClaim(text: string): Promise<ClaimResponse> {
  const response = await fetch(`${API_BASE}/check`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || "Backend request failed")
  }

  return response.json() as Promise<ClaimResponse>
}

async function postChat(
  message: string,
  sessionId: string,
  expandOnline: boolean,
  days?: number,
  context?: string,
  keywords?: string[]
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, session_id: sessionId, expand_online: expandOnline, days, context, keywords }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || "Chat backend request failed")
  }

  return response.json() as Promise<ChatResponse>
}

const VERDICT_COLORS: Record<string, string> = {
  True: "#34d399",
  False: "#f87171",
  Misleading: "#fbbf24",
  Unverifiable: "#a855f7",
}

export default function Home() {
  const [claim, setClaim] = useState("")
  const [result, setResult] = useState<ClaimResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

    const [derivedKeywords, setDerivedKeywords] = useState<string[]>([])
  // Chat state
  const [chatQuestion, setChatQuestion] = useState("")
  // Chat conversation state (for a sleek threaded UI)
  const [chatTurns, setChatTurns] = useState<Array<{
    role: "user" | "assistant"
    text: string
    citations?: string[]
    evidence?: EvidenceChunk[]
  }>>([])
  const [chatError, setChatError] = useState<string | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
    // Lightweight client-side keyword extraction (mirrors backend heuristics)
    const suggestKeywords = useCallback((q: string, ctx?: string) => {
      const basis = `${q} ${ctx ?? ""}`
      const ticks = Array.from(basis.matchAll(/\b[A-Z]{2,5}\b/g)).map((m) => m[0])
      const caps = Array.from(basis.matchAll(/\b[A-Z][a-z]{2,}\b/g)).map((m) => m[0])
      const nums = Array.from(basis.matchAll(/\b(Q[1-4]|\d{4}|\d+%|bps|YoY|yoy)\b/gi)).map((m) => m[0])
      const all = [...ticks, ...caps, ...nums]
      const seen = new Set<string>()
      const uniq = all.filter((x) => {
        const k = x.toUpperCase()
        if (seen.has(k)) return false
        seen.add(k)
        return true
      })
      return uniq.slice(0, 6)
    }, [])
  const [useOnline, setUseOnline] = useState(true)
  const [sessionId] = useState(() => `web-${Math.random().toString(36).slice(2)}`)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const contextString = result
    ? `Original claim: ${result.claim}. Verdict: ${result.result.verdict}. Reasoning: ${result.result.reasoning}.`
    : undefined

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      if (!claim.trim()) {
        setError("Please enter a financial claim.")
        return
      }
      setIsLoading(true)
      setError(null)
      setResult(null)
      try {
        const data = await postClaim(claim.trim())
        setResult(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error")
      } finally {
        setIsLoading(false)
      }
    },
    [claim]
  )

  return (
    <main>
      <section>
        <div className="badge">Financial RAG Fact-Checker</div>
        <h1 style={{ fontSize: "2.5rem", margin: "0.5rem 0 1rem" }}>
          Verify market-moving headlines before you act
        </h1>
        <p style={{ marginBottom: "2rem", color: "rgba(148,163,184,0.85)" }}>
          Enter a financial news headline or statement. We will retrieve evidence from your curated
          corpus and ask an LLM to issue a grounded verdict.
        </p>
        <form onSubmit={handleSubmit} className="card" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <label htmlFor="claim" style={{ fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", fontSize: "0.85rem", color: "rgba(148,163,184,0.9)" }}>
            Claim
          </label>
          <textarea
            id="claim"
            placeholder="e.g., Tesla reported a 20% rise in Q3 2025 revenue."
            value={claim}
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setClaim(event.target.value)}
          />
          <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
            <button type="submit" disabled={isLoading} style={isLoading ? { opacity: 0.6, pointerEvents: "none" } : undefined}>
              {isLoading ? "Running analysis..." : "Check Fact"}
            </button>
          </div>
        </form>
        {error ? (
          <div className="alert error">{error}</div>
        ) : null}
      </section>

      {result ? (
        <section className="card-grid">
          <div className="card" style={{ border: `1px solid ${VERDICT_COLORS[result.result.verdict] || "#60a5fa"}` }}>
            <div className="badge" style={{ backgroundColor: `${VERDICT_COLORS[result.result.verdict] || "#3b82f6"}33`, color: VERDICT_COLORS[result.result.verdict] || "#93c5fd" }}>
              Verdict
            </div>
            <h2 style={{ fontSize: "2rem", margin: "1rem 0", color: VERDICT_COLORS[result.result.verdict] || "#bfdbfe" }}>
              {result.result.verdict}
            </h2>
            <table className="table">
              <tbody>
                <tr>
                  <td>Confidence</td>
                  <td>{result.result.confidence.toFixed(2)}</td>
                </tr>
                <tr>
                  <td>Reasoning</td>
                  <td>{result.result.reasoning}</td>
                </tr>
                <tr>
                  <td>Citations</td>
                  <td>
                    {result.result.citations.length > 0 ? result.result.citations.join(", ") : "No citations provided"}
                  </td>
                </tr>
              </tbody>
            </table>
            {result.result.verdict === "Unverifiable" ? (
              <div className="alert" style={{ marginTop: "1rem" }}>
                This claim couldn’t be verified with your local corpus. Use the Follow-up Q&A panel (bottom-right) and enable “Use online sources” to search trusted live feeds.
              </div>
            ) : null}
          </div>

          <div className="card">
            <div className="badge" style={{ backgroundColor: "rgba(56,189,248,0.25)", color: "#bae6fd" }}>
              Evidence
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "1.5rem" }}>
              {result.evidence.map((item, index) => (
                <article key={`${item.source}-${item.chunk_index ?? index}`} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <header style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                    <strong style={{ fontSize: "1rem", letterSpacing: "0.03em", textTransform: "uppercase", color: "rgba(148,163,184,0.9)" }}>
                      {item.source}
                    </strong>
                    <small style={{ color: "rgba(148,163,184,0.65)" }}>Similarity score: {item.score.toFixed(3)}</small>
                  </header>
                  <p style={{ margin: 0, lineHeight: 1.6, color: "rgba(226,232,240,0.92)" }}>{item.text}</p>
                </article>
              ))}
            </div>
          </div>

          {/* Floating Follow-up Q&A button and sliding drawer */}
          <button
            onClick={() => setDrawerOpen((v) => !v)}
            style={{
              position: "fixed",
              right: "1rem",
              bottom: "1rem",
              zIndex: 50,
              padding: "0.75rem 1rem",
            }}
          >
            {drawerOpen ? "Close Q&A" : "Follow-up Q&A"}
          </button>

          <div
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              height: "100vh",
              width: "min(520px, 100%)",
              background: "rgba(2,6,23,0.98)",
              borderLeft: "1px solid rgba(148,163,184,0.2)",
              transform: drawerOpen ? "translateX(0%)" : "translateX(100%)",
              transition: "transform 200ms ease-in-out",
              zIndex: 40,
              display: "flex",
              flexDirection: "column",
              padding: "1rem",
              gap: "1rem",
            }}
          >
            <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div className="badge" style={{ backgroundColor: "rgba(34,197,94,0.25)", color: "#bbf7d0" }}>
                Follow-up Q&A
              </div>
              <button onClick={() => setDrawerOpen(false)} aria-label="Close Q&A" style={{ padding: "0.25rem 0.5rem" }}>
                ×
              </button>
            </header>
            <small style={{ color: "rgba(148,163,184,0.9)", marginTop: "-0.25rem" }}>
              {contextString ? contextString : "Ask a clarifying question about your earlier claim."}
            </small>
            <form
              onSubmit={async (e) => {
                e.preventDefault()
                if (!chatQuestion.trim()) return
                setChatLoading(true)
                setChatError(null)
                try {
                  // optimistic user turn
                  setChatTurns((prev) => [...prev, { role: "user", text: chatQuestion.trim() }])

                  const data = await postChat(
                    chatQuestion.trim(),
                    sessionId,
                    useOnline,
                    undefined,
                    contextString,
                    derivedKeywords.length ? derivedKeywords : undefined
                  )
                  // assistant turn
                  setChatTurns((prev) => [
                    ...prev,
                    {
                      role: "assistant",
                      text: data.result.answer,
                      citations: data.result.citations,
                      evidence: data.evidence,
                    },
                  ])
                  setChatQuestion("")
                } catch (err) {
                  setChatError(err instanceof Error ? err.message : "Unexpected error")
                } finally {
                  setChatLoading(false)
                }
              }}
              style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
            >
              {derivedKeywords.length ? (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {derivedKeywords.map((kw) => (
                    <span
                      key={kw}
                      title="Auto-extracted keyword"
                      style={{
                        background: "rgba(148,163,184,0.12)",
                        border: "1px solid rgba(148,163,184,0.3)",
                        borderRadius: "999px",
                        padding: "0.25rem 0.6rem",
                        fontSize: "0.8rem",
                        color: "rgba(226,232,240,0.9)",
                      }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              ) : null}
              <input
                id="chat-q"
                type="text"
                placeholder="e.g., What happened with Apple and Tesla?"
                value={chatQuestion}
                onChange={(e) => {
                  const v = e.target.value
                  setChatQuestion(v)
                  const kws = suggestKeywords(v, contextString)
                  setDerivedKeywords(kws)
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    const form = (e.currentTarget as HTMLInputElement).form
                    form?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }))
                  }
                }}
              />
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input type="checkbox" checked={useOnline} onChange={(e) => setUseOnline(e.target.checked)} />
                <span>Use online sources</span>
              </label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button type="submit" disabled={chatLoading} style={chatLoading ? { opacity: 0.6, pointerEvents: "none" } : undefined}>
                  {chatLoading ? "Answering…" : "Ask"}
                </button>
                <button type="button" onClick={() => setChatQuestion("")}>Clear</button>
              </div>
            </form>

            {chatError ? <div className="alert error">{chatError}</div> : null}

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", overflowY: "auto" }}>
              {chatTurns.map((turn, idx) => (
                <div
                  key={idx}
                  style={{
                    alignSelf: turn.role === "user" ? "flex-end" : "flex-start",
                    maxWidth: "82%",
                  }}
                >
                  <div
                    className="card"
                    style={{
                      background: turn.role === "user" ? "rgba(99,102,241,0.25)" : "rgba(15,23,42,0.45)",
                    }}
                  >
                    <p style={{ margin: 0 }}>{turn.text}</p>
                    {turn.citations && turn.citations.length ? (
                      <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                        {turn.citations.map((c) => {
                          // crude URL detection for clickable citations
                          const match = c.match(/https?:\/\/\S+/)
                          const url = match ? match[0] : null
                          return (
                            <a
                              key={c}
                              href={url || undefined}
                              target={url ? "_blank" : undefined}
                              rel={url ? "noreferrer" : undefined}
                              style={{
                                textDecoration: "none",
                                background: "rgba(148,163,184,0.12)",
                                border: "1px solid rgba(148,163,184,0.3)",
                                borderRadius: "999px",
                                padding: "0.15rem 0.45rem",
                                fontSize: "0.78rem",
                                color: "rgba(226,232,240,0.9)",
                              }}
                              title={c}
                            >
                              {url ? "Link" : c}
                            </a>
                          )
                        })}
                      </div>
                    ) : null}
                  </div>
                  {turn.evidence && turn.evidence.length ? (
                    <details style={{ marginTop: "0.35rem" }}>
                      <summary style={{ cursor: "pointer", color: "rgba(148,163,184,0.95)" }}>View evidence</summary>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.5rem" }}>
                        {turn.evidence.map((ev, i) => (
                          <article key={`${ev.source}-${ev.chunk_index ?? i}`}>
                            <strong style={{ color: "rgba(148,163,184,0.9)" }}>{ev.source}</strong>
                            <small style={{ display: "block", color: "rgba(148,163,184,0.65)" }}>
                              Similarity score: {ev.score.toFixed(3)}
                            </small>
                            <p style={{ marginTop: "0.35rem" }}>{ev.text}</p>
                          </article>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  )
}
