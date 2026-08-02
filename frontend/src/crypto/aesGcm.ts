// Client-side AES-256-GCM via the Web Crypto API. Everything here runs in
// the browser before the secret ever reaches our backend - the server (and
// Mongo, and anyone with Redis/Mongo access) only ever sees the output of
// encryptToPayload(): opaque ciphertext + IV, never plaintext, never the
// key. The key never leaves the browser except as a URL fragment, which is
// never transmitted to any server (see pages/ViewSecret.tsx in a later stage).

const ALGORITHM = "AES-GCM";
const KEY_LENGTH_BITS = 256;

// 96 bits is the length AES-GCM is designed for - a longer IV gets hashed
// down via GHASH before use, which is both slower and (per NIST SP 800-38D)
// gives a weaker uniqueness guarantee than a directly-used 96-bit IV.
const IV_LENGTH_BYTES = 12;

export async function generateKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey({ name: ALGORITHM, length: KEY_LENGTH_BITS }, true, [
    "encrypt",
    "decrypt",
  ]);
}

export async function exportKeyToFragment(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey("raw", key);
  return toBase64Url(new Uint8Array(raw));
}

export async function importKeyFromFragment(fragmentValue: string): Promise<CryptoKey> {
  const raw = fromBase64Url(fragmentValue);
  // extractable: false - once the recipient's browser has imported the
  // key to decrypt, there's no legitimate reason for this app to ever
  // export it again.
  return crypto.subtle.importKey("raw", raw as BufferSource, ALGORITHM, false, ["decrypt"]);
}

// Encodes IV + ciphertext into a single base64url string, matching the
// backend's `content: str` field exactly - the backend doesn't need to
// know or care about our encryption scheme, it just stores opaque bytes.
export async function encryptToPayload(plaintext: string, key: CryptoKey): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH_BYTES));
  const encoded = new TextEncoder().encode(plaintext);
  const ciphertext = await crypto.subtle.encrypt({ name: ALGORITHM, iv }, key, encoded);

  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);
  return toBase64Url(combined);
}

export async function decryptFromPayload(payload: string, key: CryptoKey): Promise<string> {
  const combined = fromBase64Url(payload);
  const iv = combined.slice(0, IV_LENGTH_BYTES);
  const ciphertext = combined.slice(IV_LENGTH_BYTES);

  // subtle.decrypt verifies GCM's authentication tag as part of
  // decrypting - a wrong key or a single flipped bit in the ciphertext
  // throws here rather than silently returning garbage. We let that
  // exception propagate; callers treat "decryption failed" as "the link
  // is wrong or the payload was tampered with," not a bug to recover from.
  const plaintextBuffer = await crypto.subtle.decrypt({ name: ALGORITHM, iv }, key, ciphertext);
  return new TextDecoder().decode(plaintextBuffer);
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(value: string): Uint8Array {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const withPadding = padded.padEnd(padded.length + ((4 - (padded.length % 4)) % 4), "=");
  const binary = atob(withPadding);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
