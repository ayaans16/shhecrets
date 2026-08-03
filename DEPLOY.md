# Deploying to the VPS

One-time setup + the steps to bring the stack up. Run everything below
directly on the VPS unless noted otherwise.

## 1. Cloudflare (one-time, dashboard)

DNS records - already done:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `shhecrets.ca` | VPS IP | Proxied |
| A | `api.shhecrets.ca` | VPS IP | Proxied |

Still needed:

1. **SSL/TLS → Overview → set mode to "Full (strict)".**
2. **SSL/TLS → Origin Server → Create Certificate.**
   - Hostnames: `shhecrets.ca`, `api.shhecrets.ca`
   - Key type: RSA 2048 (default is fine)
   - Save the certificate as `cert.pem` and the private key as `key.pem`.

## 2. Place the origin certificate on the VPS

Copy the cert and key straight from the Cloudflare dashboard into these
files, directly in your VPS terminal session - never paste a private
key anywhere else (chat, email, a shared doc). A heredoc handles
multi-line PEM content more reliably than a text editor's paste mode:

```bash
mkdir -p infra/certs

cat > infra/certs/cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
EOF

cat > infra/certs/key.pem << 'EOF'
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
EOF

chmod 600 infra/certs/key.pem
```

`infra/certs/` is gitignored - it never gets committed, only ever lives
on the VPS. If this key is ever pasted somewhere it shouldn't be (chat,
a ticket, a log), revoke and regenerate it in Cloudflare - Origin
Certificates are free and instant to reissue.

## 3. Backend secrets

```bash
cp backend/.env.production.example backend/.env.production
```

Edit `backend/.env.production`:
- `IP_HASH_PEPPER` - generate a real one: `openssl rand -hex 32`. Do
  **not** reuse the value in `.env.example` - that one is committed to
  the repo and public.
- Confirm `CORS_ORIGINS=https://shhecrets.ca` (no dev ports).

`backend/.env.production` is gitignored too.

## 4. Bring the stack up

```bash
cd infra
docker compose -f docker-compose.prod.yml up -d --build
```

## 5. Verify

```bash
curl https://shhecrets.ca/                 # frontend, should return the app's HTML
curl https://api.shhecrets.ca/health       # {"status":"ok"}

# full flow
curl -X POST https://api.shhecrets.ca/sessions
```

Then open `https://shhecrets.ca` in a browser and run through the real
create -> copy link -> reveal flow end to end.

```bash
docker compose -f docker-compose.prod.yml ps
# only `proxy` should show published ports (80, 443)
```

## 6. Automated deploys (GitHub Actions, one-time setup)

After this, every merge to `main` that passes CI automatically redeploys
the VPS.

**Generate a dedicated deploy key directly on the VPS** - don't reuse
your personal SSH key, and don't generate it anywhere the private key
would need to travel between machines:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/gh_actions_deploy -N ""
cat ~/.ssh/gh_actions_deploy.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/gh_actions_deploy   # copy this - the private key
```

**Add three repository secrets** (GitHub repo -> Settings -> Secrets and
variables -> Actions -> New repository secret). Paste values directly
into GitHub's secret UI - never into chat, a commit, or a file in the
repo:

| Secret | Value |
|---|---|
| `VPS_HOST` | the VPS's public IP |
| `VPS_USER` | `ubuntu` (or whatever user you SSH in as) |
| `VPS_SSH_KEY` | the private key from `cat ~/.ssh/gh_actions_deploy` above |

That's it - the next push to `main` that passes CI will SSH in, `git
pull`, rebuild, and curl the public health endpoint to confirm it came
up. Watch it under the repo's Actions tab.

## Day-to-day operations

```bash
# logs
docker compose -f docker-compose.prod.yml logs -f backend

# restart everything
docker compose -f docker-compose.prod.yml restart

# deploy new code (until CI/CD automates this)
git pull
docker compose -f docker-compose.prod.yml up -d --build

# tear down (keeps volumes - mongo data, caddy state)
docker compose -f docker-compose.prod.yml down

# tear down AND wipe volumes (destroys mongo data)
docker compose -f docker-compose.prod.yml down -v
```
