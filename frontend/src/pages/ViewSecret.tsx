import { useState } from "react";
import { ApiError, readSecret } from "../api/client";
import { decryptFromPayload, importKeyFromFragment } from "../crypto/aesGcm";

type Phase = "gated" | "revealing" | "revealed" | "error";

interface Props {
  sessionId: string;
}

function getFragmentKey(): string | null {
  // The key lives only in the fragment (after #), which browsers never
  // send anywhere - not in the request, not in the Referer header. This
  // is the only place in the app that reads it.
  const params = new URLSearchParams(window.location.hash.slice(1));
  return params.get("key");
}

export default function ViewSecret({ sessionId }: Props) {
  const [phase, setPhase] = useState<Phase>("gated");
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Revealing requires an explicit click rather than fetching as soon as
  // the page loads. That's deliberate: this is a delete-on-read secret,
  // and plenty of things auto-fetch links before a human ever sees them -
  // Slack/iMessage/Teams unfurling a link preview, a corporate email
  // scanner, etc. Any of those would silently burn the secret before the
  // real recipient opens the page if we fetched on mount.
  async function handleReveal() {
    const fragmentKey = getFragmentKey();
    if (!fragmentKey) {
      setError("This link is missing its decryption key - it may have been copied incorrectly.");
      setPhase("error");
      return;
    }

    setPhase("revealing");
    setError(null);
    try {
      // This call burns the secret server-side the moment it succeeds -
      // if decryption fails afterward (corrupted/wrong key), the secret
      // is still gone. The backend has no way to know a fetch was
      // followed by a failed decrypt, only that a fetch happened.
      const payload = await readSecret(sessionId);
      const key = await importKeyFromFragment(fragmentKey);
      const plaintext = await decryptFromPayload(payload, key);
      setSecret(plaintext);
      setPhase("revealed");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Fetched the secret but couldn't decrypt it - the link's key may be corrupted.",
      );
      setPhase("error");
    }
  }

  async function handleCopy() {
    if (!secret) return;
    await navigator.clipboard.writeText(secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (phase === "gated") {
    return (
      <div className="card stack">
        <h1>someone shared a secret with you</h1>
        <p>
          This can be viewed exactly once. As soon as you reveal it, it's permanently destroyed -
          closing this tab, losing the link, or reloading the page afterward means it's gone for
          good.
        </p>
        <button className="btn" onClick={handleReveal}>
          reveal secret
        </button>
      </div>
    );
  }

  if (phase === "revealing") {
    return (
      <div className="card stack">
        <p className="muted">revealing…</p>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="card stack">
        <h1>can't show this secret</h1>
        <p className="status status-danger">{error}</p>
        <p className="faint">
          This usually means the link was already used, expired, or was copied incorrectly.
        </p>
      </div>
    );
  }

  return (
    <div className="card stack">
      <span className="badge badge-success">revealed - now permanently deleted</span>
      <div className="secret-reveal">{secret}</div>
      <button className="btn-secondary" onClick={handleCopy}>
        {copied ? "copied" : "copy to clipboard"}
      </button>
      <p className="faint">This won't be shown again. Save it somewhere safe if you still need it.</p>
    </div>
  );
}
