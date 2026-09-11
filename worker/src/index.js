// In the Black — ICE credential minter
//
// Why this exists: the game forces iceTransportPolicy:'relay' so that two
// players never learn each other's IP address. That needs TURN credentials,
// and the game is a public static page, so it cannot hold the long-term key —
// anyone could read it and mint unlimited credentials on the account.
//
// This Worker holds the key and hands out credentials that expire in an hour.
//
// It deliberately reads nothing about the caller. No IP, no User-Agent, no
// logging of any kind: the point of the relay is that nobody collects player
// addresses, and that includes us.

const TTL_SECONDS = 3600;

export default {
  async fetch(request, env) {
    // ALLOWED_ORIGIN is a comma-separated allowlist. Echo the caller's origin
    // back when it matches, since Access-Control-Allow-Origin cannot carry a
    // list. Hygiene only — a non-browser client forges Origin trivially, so
    // the real limits are the 1-hour TTL and revocation via the TURN key.
    const allowed = (env.ALLOWED_ORIGIN || '*').split(',').map((o) => o.trim()).filter(Boolean);
    const reqOrigin = request.headers.get('Origin') || '';
    const origin = allowed.includes('*')
      ? '*'
      : (allowed.includes(reqOrigin) ? reqOrigin : allowed[0] || '*');
    const cors = {
      'Access-Control-Allow-Origin': origin,
      'Vary': 'Origin',
      'Cache-Control': 'no-store',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== 'GET' && request.method !== 'POST') {
      return json({ error: 'method not allowed' }, 405, cors);
    }
    const KEY_ID = (env.TURN_KEY_ID || '').trim();
    const KEY_TOKEN = (env.TURN_KEY_TOKEN || '').trim();
    if (!KEY_ID || !KEY_TOKEN) {
      // Name which binding is absent. "not configured" alone sent us hunting
      // through deployments and secret lists for something this would have
      // answered immediately. It reveals nothing a caller can use — the
      // generic error already told them the relay was unconfigured.
      // Distinguish absent from present-but-empty. A binding can exist and
      // still be an empty string if the interactive prompt was answered with a
      // bare Enter, and "missing" alone cannot tell those apart. Lengths only —
      // never the values.
      const state = (v) => (v === undefined || v === null ? 'absent' : (String(v).trim() === '' ? 'empty' : 'set:' + String(v).trim().length));
      return json({
        error: 'relay not configured',
        TURN_KEY_ID: state(env.TURN_KEY_ID),
        TURN_KEY_TOKEN: state(env.TURN_KEY_TOKEN),
      }, 500, cors);
    }

    const url = `https://rtc.live.cloudflare.com/v1/turn/keys/${KEY_ID}/credentials/generate-ice-servers`;

    let upstream;
    try {
      upstream = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${KEY_TOKEN}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ttl: TTL_SECONDS }),
      });
    } catch (err) {
      // err.message only - never the error object, which can carry socket detail
      return json({ error: 'relay provider unreachable' }, 502, cors);
    }

    if (!upstream.ok) {
      return json({ error: `relay provider returned ${upstream.status}` }, 502, cors);
    }

    const data = await upstream.json();

    // Cloudflare's docs show iceServers already as an array of one object
    // carrying a urls array, which is the shape RTCPeerConnection wants. The
    // Array.isArray guard below stays anyway: it costs nothing and it means a
    // bare object would still work if the response shape ever changes.
    let iceServers = data && data.iceServers;
    if (!iceServers) return json({ error: 'relay provider returned no ICE servers' }, 502, cors);
    if (!Array.isArray(iceServers)) iceServers = [iceServers];

    return json({ iceServers }, 200, cors);
  },
};

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers, 'Content-Type': 'application/json' },
  });
}
