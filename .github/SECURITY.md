# Security Policy

## Supported versions

shhecrets is a single, continuously-deployed application, not a versioned library — the `main` branch is always the supported version, live at https://shhecrets.ca. There are no older versions receiving patches.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, email **ayaannshaikhh8@gmail.com** with:
- A description of the issue and its potential impact
- Steps to reproduce, if possible
- Any relevant logs, payloads, or screenshots

I'll acknowledge reports within a few days. Since this is a single-maintainer personal project (not a funded product), there's no bug bounty, but genuine reports are taken seriously and credited if you'd like.

## Security model

This is the part that actually matters for this project, since the entire point of shhecrets is the security guarantee it makes. Briefly:

- **Client-side encryption only.** Secrets are encrypted in the browser with AES-256-GCM (Web Crypto API) before any network request is made. The decryption key never leaves the browser except as a URL fragment (`#key=...`), which browsers never transmit to any server — not in the request line, not in `Referer` headers, not in server logs.
- **The backend only ever sees ciphertext.** There is no server-side decryption path anywhere in the codebase. A full compromise of the backend, Redis, or MongoDB would expose ciphertext, never plaintext.
- **Delete-on-read is atomic.** Reading a secret uses Redis's `GETDEL`, a single atomic command — two simultaneous requests for the same secret cannot both succeed.
- **Session IDs are CSPRNG-generated**, 256 bits of entropy, making brute-force guessing of a live session URL infeasible.
- **Rate limiting** is applied to both session creation and reads, keyed by the real client IP (`CF-Connecting-IP` behind Cloudflare) to slow down enumeration attempts.
- **IP addresses are never stored raw.** MongoDB's audit trail stores a salted SHA-256 hash of the creator's IP, never the IP itself.
- **No plaintext secret content is ever logged**, in application logs, error messages, or metrics.

## Known limitations

Worth being upfront about, since "secure" is a claim that deserves scrutiny:

- Session TTL is fixed (10 minutes by default) and not user-configurable from the UI.
- There's no optional passphrase layer beyond the link itself — anyone who obtains the full link (including the fragment) before the legitimate recipient can read the secret.
- Single-VPS deployment: no redundancy. A VPS-level compromise would expose ciphertext + metadata, though not plaintext (see above).
- No automated dependency vulnerability scanning is currently configured in CI.

If you find a gap not listed here, that's exactly what the reporting process above is for.
