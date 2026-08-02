// Thin typed wrapper around the backend's session API. Deliberately dumb
// about encryption - it transports whatever string it's given as `content`
// (ciphertext, produced by crypto/aesGcm.ts before this module is ever
// called) and has no idea it's opaque bytes rather than plaintext. Keeping
// that boundary here means a bug in this file can leak metadata (timing,
// status codes) but never the secret itself.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface CreatedSession {
  sessionId: string;
  expiresAt: Date;
}

export async function createSession(): Promise<CreatedSession> {
  const res = await fetch(`${API_BASE_URL}/sessions`, { method: "POST" });
  if (!res.ok) {
    throw new ApiError(await extractErrorDetail(res), res.status);
  }
  const body = await res.json();
  return { sessionId: body.session_id, expiresAt: new Date(body.expires_at) };
}

export async function submitSecret(sessionId: string, encryptedContent: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/secret`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: encryptedContent }),
  });
  if (!res.ok) {
    throw new ApiError(await extractErrorDetail(res), res.status);
  }
}

// Returns the raw encrypted payload exactly as stored - decryption happens
// client-side afterward, using the key from the URL fragment (which this
// module never sees; it's not part of any request we make).
export async function readSecret(sessionId: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) {
    throw new ApiError(await extractErrorDetail(res), res.status);
  }
  const body = await res.json();
  return body.content;
}

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Response body wasn't JSON (or had no `detail`) - fall through to a
    // generic message rather than throwing from inside error handling.
  }
  return `Request failed with status ${res.status}`;
}
