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
    const origin = env.ALLOWED_ORIGIN || '*';
    const cors = {
      'Access-Control-Allow-Origin': origin,
      'Cache-Control': 'no-store',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== 'GET' && request.method !== 'POST') {
      return json({ error: 'method not allowed' }, 405, cors);
    }
    if (!env.TURN_KEY_ID || !env.TURN_KEY_TOKEN) {
      return json({ error: 'relay not configured' }, 500, cors);
    }

    const url = `https://rtc.live.cloudflare.com/v1/turn/keys/${env.TURN_KEY_ID}/credentials/generate-ice-servers`;

    let upstream;
    try {
      upstream = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.TURN_KEY_TOKEN}`,
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

    // Cloudflare returns iceServers as a SINGLE object with a urls array.
    // RTCPeerConnection wants a sequence, so normalise to an array here
    // rather than making the game guess.
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
