import { describe, expect, it } from "vitest";
import {
  decryptFromPayload,
  encryptToPayload,
  exportKeyToFragment,
  generateKey,
  importKeyFromFragment,
} from "./aesGcm";

describe("aesGcm", () => {
  it("round-trips plaintext through encrypt/decrypt with the same key", async () => {
    const key = await generateKey();
    const plaintext = "DB_PASSWORD=hunter2\nAPI_KEY=sk-abc123";

    const payload = await encryptToPayload(plaintext, key);
    const decrypted = await decryptFromPayload(payload, key);

    expect(decrypted).toBe(plaintext);
  });

  it("never leaks plaintext into the encrypted payload", async () => {
    const key = await generateKey();
    const plaintext = "super-secret-value-should-not-appear-verbatim";

    const payload = await encryptToPayload(plaintext, key);

    expect(payload).not.toContain(plaintext);
  });

  it("round-trips a key through export (fragment) and import", async () => {
    const key = await generateKey();
    const plaintext = "round trip via the exported fragment key";

    const fragmentKey = await exportKeyToFragment(key);
    const importedKey = await importKeyFromFragment(fragmentKey);

    const payload = await encryptToPayload(plaintext, key);
    const decrypted = await decryptFromPayload(payload, importedKey);

    expect(decrypted).toBe(plaintext);
  });

  it("rejects decryption with the wrong key", async () => {
    const key = await generateKey();
    const wrongKey = await generateKey();
    const payload = await encryptToPayload("only decryptable with the right key", key);

    await expect(decryptFromPayload(payload, wrongKey)).rejects.toThrow();
  });

  it("rejects a tampered ciphertext (GCM auth tag catches it)", async () => {
    const key = await generateKey();
    const payload = await encryptToPayload("tamper-proof, hopefully", key);

    // Flip the last base64url character - corrupts the trailing byte of
    // the auth tag (or ciphertext), which GCM must detect.
    const tampered = payload.slice(0, -1) + (payload.at(-1) === "A" ? "B" : "A");

    await expect(decryptFromPayload(tampered, key)).rejects.toThrow();
  });

  it("produces a different ciphertext each time (random IV per encryption)", async () => {
    const key = await generateKey();
    const plaintext = "same plaintext, different payload every time";

    const payloadA = await encryptToPayload(plaintext, key);
    const payloadB = await encryptToPayload(plaintext, key);

    expect(payloadA).not.toBe(payloadB);
  });
});
