# ICE credential minter

Hands the game short-lived TURN credentials so online play can run relay-only
and players never learn each other's IP addresses.

The long-term Cloudflare TURN key lives only in Worker secrets. It must never
be committed here — this repository is public.

## Deploy

1. **Create a TURN key.** Cloudflare dashboard → Realtime → TURN → create a key.
   Keep the **Key ID** and the **API token**.

2. **Install wrangler** (once):

       npm install -g wrangler
       wrangler login

3. **Store the secrets.** These are entered interactively and never written to
   disk in this repo:

       cd worker
       wrangler secret put TURN_KEY_ID
       wrangler secret put TURN_KEY_TOKEN

4. **Deploy:**

       wrangler deploy

   It prints a URL like `https://itb-ice.<your-subdomain>.workers.dev`.

5. **Point the game at it.** In `index.html`, set:

       const ITB_ICE_ENDPOINT = 'https://itb-ice.<your-subdomain>.workers.dev';

   That URL is not a secret and is fine to commit.

6. **Check it:**

       curl -s https://itb-ice.<your-subdomain>.workers.dev | head -c 300

   Expect `{"iceServers":[{"urls":[...],"username":"...","credential":"..."}]}`.
   Credentials expire after an hour, so the value changing between calls is
   correct.

## Deploy order matters

Set the secrets **after** the final `wrangler deploy`, never before.

`wrangler deploy` rebuilds the Worker's bindings from `wrangler.toml`, and the
secrets are not in there (deliberately — this repo is public). They survive in
`wrangler secret list` but stop being bound at runtime, so the Worker answers
`{"error":"relay not configured","missing":[...]}` while the secrets appear to
exist. `--keep-vars` does not rescue this.

A `wrangler secret put` creates its own version inheriting the current code, so
secrets-last always works. If you ever redeploy the code, re-add both secrets
afterwards.

## Cost

Cloudflare Realtime TURN bills relay egress: the free allowance is 1,000 GB,
against roughly 0.16 GB per hour of play — about 6,300 hours a month. The
Worker itself is on the free plan's 100,000 requests/day, and the game calls it
once per match.

There is no documented spend cap past the free allowance, which is exactly why
the key stays in here instead of in the page. If a credential ever leaks it
expires within the hour, and the TURN key can revoke already-issued ones.

## Privacy

This Worker reads nothing about the caller and logs nothing. Don't add
request logging, analytics, or an error handler that prints the error object
rather than `err.message` — any of those can capture player IP addresses,
which defeats the reason the relay is here.
