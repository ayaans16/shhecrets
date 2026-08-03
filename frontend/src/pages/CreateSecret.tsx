import { useState } from "react";
import { ApiError, createSession, submitSecret } from "../api/client";
import { encryptToPayload, exportKeyToFragment, generateKey } from "../crypto/aesGcm";

// Must match backend/app/models/session.py's SecretSubmission.max_length.
// Checking client-side first avoids a wasted round trip for the common
// case of someone pasting something way too large; the backend's own
// limit is still what's actually enforced.
const MAX_SECRET_LENGTH = 64_000;

type Phase = "idle" | "creating" | "ready" | "saving" | "saved" | "error";

interface ActiveSession {
  sessionId: string;
  expiresAt: Date;
  key: CryptoKey;
  link: string;
}

function buildShareLink(sessionId: string, fragmentKey: string): string {
  // The key lives only in the fragment (after #) - fragments are never
  // sent to any server, never appear in server logs, and aren't included
  // in the Referer header when this link is followed.
  return `${window.location.origin}/s/${sessionId}#key=${fragmentKey}`;
}

function minutesUntil(date: Date): number {
  return Math.max(0, Math.round((date.getTime() - Date.now()) / 60_000));
}

export default function CreateSecret() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [session, setSession] = useState<ActiveSession | null>(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleStart() {
    setPhase("creating");
    setError(null);
    try {
      // Independent of each other - the key never touches the backend
      // at any point, including this call, so there's no reason to wait
      // on one before starting the other.
      const [key, created] = await Promise.all([generateKey(), createSession()]);
      const fragmentKey = await exportKeyToFragment(key);
      setSession({
        sessionId: created.sessionId,
        expiresAt: created.expiresAt,
        key,
        link: buildShareLink(created.sessionId, fragmentKey),
      });
      setPhase("ready");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start a session. Try again.");
      setPhase("error");
    }
  }

  async function handleSave() {
    if (!session || !content.trim()) return;
    setPhase("saving");
    setError(null);
    try {
      const payload = await encryptToPayload(content, session.key);
      await submitSecret(session.sessionId, payload);
      setContent(""); // don't keep plaintext around in state longer than needed
      setPhase("saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the secret. Try again.");
      setPhase("ready");
    }
  }

  async function handleCopy() {
    if (!session) return;
    await navigator.clipboard.writeText(session.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleReset() {
    setSession(null);
    setContent("");
    setError(null);
    setPhase("idle");
  }

  if (phase === "idle" || phase === "creating") {
    return (
      <div className="stack">
        <h1>share a secret, once</h1>
        <p>
          Start a session to get a one-time link. Paste in an API key, a .env file, credentials -
          whatever needs to reach someone without living anywhere forever. It's encrypted in your
          browser before it ever reaches this server, and destroyed the instant it's read.
        </p>
        <button className="btn" onClick={handleStart} disabled={phase === "creating"}>
          {phase === "creating" ? "starting…" : "start session"}
        </button>
        {error && <p className="status status-danger">{error}</p>}
      </div>
    );
  }

  const overLimit = content.length > MAX_SECRET_LENGTH;

  return (
    <div className="stack">
      <div className="card stack">
        <span className="badge">expires in ~{minutesUntil(session!.expiresAt)} min</span>
        <div className="link-box">
          <code>{session!.link}</code>
          <button className="btn-secondary" onClick={handleCopy}>
            {copied ? "copied" : "copy"}
          </button>
        </div>
        <p className="faint">
          This link contains the decryption key. Anyone with it can read the secret exactly once -
          share it only over a channel you trust.
        </p>
      </div>

      {phase !== "saved" ? (
        <div className="card stack">
          <textarea
            rows={8}
            placeholder="paste the secret here - an API key, .env contents, credentials..."
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={phase === "saving"}
          />
          {overLimit && (
            <p className="status status-danger">
              too long ({content.length.toLocaleString()} / {MAX_SECRET_LENGTH.toLocaleString()}{" "}
              characters)
            </p>
          )}
          <button
            className="btn"
            onClick={handleSave}
            disabled={phase === "saving" || !content.trim() || overLimit}
          >
            {phase === "saving" ? "encrypting & saving…" : "encrypt & save"}
          </button>
          {error && <p className="status status-danger">{error}</p>}
        </div>
      ) : (
        <div className="card stack">
          <p className="status status-success">saved - the link above is ready to share</p>
          <button className="btn-secondary" onClick={handleReset}>
            start another session
          </button>
        </div>
      )}
    </div>
  );
}
