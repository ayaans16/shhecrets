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

## 7. Backups (Mongo -> AWS S3)

Redis isn't backed up - see `scripts/backup-mongo.sh` for why.

**Set a budget alert first, before creating anything else.** AWS
Billing -> Budgets -> Create budget -> fixed amount, e.g. $1 -> alert
via email at 100% of actual spend. This is the real safety net - it's
what actually catches "something's gone wrong" before it becomes a
real bill, not the free-tier math below.

**Create the bucket** (S3 console -> Create bucket -> name
`shhecrets-backups`, or a suffixed variant if that's taken since bucket
names are globally unique -> keep "Block all public access" on, the
default).

**Set a lifecycle rule for retention** (bucket -> Management ->
Lifecycle rules -> add rule -> expire objects after e.g. 30 days) -
this is what handles cleanup, not the script.

**Create a dedicated IAM user** (IAM -> Users -> Create user, no
console access needed) - don't use root account credentials for this,
or for anything else. Attach this inline policy, scoped to only this
one bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketOnly",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::shhecrets-backups"
    },
    {
      "Sid": "ReadWriteObjectsOnly",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::shhecrets-backups/*"
    }
  ]
}
```

Not the AWS-managed `AmazonS3FullAccess` policy - that would grant
access to every bucket in the account, not just this one. Then
generate an access key for this user (Security credentials -> Create
access key -> "Command Line Interface (CLI)" use case).

**Install the AWS CLI on the VPS:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
sudo apt-get install -y unzip
unzip awscliv2.zip
sudo ./aws/install
```

**Configure credentials directly on the VPS** (paste the Access Key
ID/Secret Access Key when prompted - never here):
```bash
aws configure
# AWS Access Key ID: <paste>
# AWS Secret Access Key: <paste>
# Default region: <your bucket's region, e.g. us-east-1>
# Default output format: json
```

**Test it once manually**, then check the bucket:
```bash
cd ~/shhecrets
ALERT_EMAIL=you@example.com ./scripts/backup-mongo.sh
aws s3 ls s3://shhecrets-backups/mongo/
```

**Add the cron job** (`crontab -e`):
```
0 3 * * * ALERT_EMAIL=you@example.com /home/ubuntu/shhecrets/scripts/backup-mongo.sh >> /home/ubuntu/shhecrets-backup.log 2>&1
```

## 8. Monitoring

Two layers - they catch different failure modes.

**A. External uptime check** (catches "the VPS itself is unreachable" -
something monitoring *from* the VPS can't detect about itself):

Sign up free at [UptimeRobot](https://uptimerobot.com) (or similar) and
add two HTTPS monitors, 5-minute interval:
- `https://shhecrets.ca`
- `https://api.shhecrets.ca/health`

Set an email alert contact so you're notified the moment either stops
responding.

**B. Local health + disk check** (catches "site's reachable but a
container's crash-looping, or disk is filling up" - things an external
ping alone won't see):

Install msmtp:
```bash
sudo apt-get install -y msmtp msmtp-mta
```

Generate a Gmail **App Password** (Google Account -> Security -> 2-Step
Verification -> App passwords) - not your real account password, Gmail
won't accept that for SMTP auth. Create `~/.msmtprc`:
```
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt

account        default
host           smtp.gmail.com
port           587
user           your-address@gmail.com
password       your-16-char-app-password
from           your-address@gmail.com
```
```bash
chmod 600 ~/.msmtprc
```

Test it once:
```bash
cd ~/shhecrets
ALERT_EMAIL=you@example.com ./scripts/healthcheck.sh; echo "exit: $?"
```
Exit `0` with no output means healthy. To confirm the email path itself
works, temporarily lower `DISK_THRESHOLD_PERCENT` in the script to
something you're already above, rerun, then put it back.

**Add the cron job:**
```
*/15 * * * * ALERT_EMAIL=you@example.com /home/ubuntu/shhecrets/scripts/healthcheck.sh >> /home/ubuntu/shhecrets-healthcheck.log 2>&1
```

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
