# IN THE BLACK — Multiplayer Architecture

## Overview

WebRTC peer-to-peer multiplayer using **PeerJS** for signaling. No dedicated game server required. One player hosts (gets a 4-character room code), the other joins with the code.

## Architecture: Host-Authoritative P2P

```
  HOST (P1)                          CLIENT (P2)
  Runs game simulation    <--input-- Sends local input
  Reads local P1 input    --state--> Receives game state
  Sends state @ ~45Hz                Interpolates + renders
            |                              |
            +--- PeerJS DataChannel -------+
                 (signaling via PeerJS cloud)
```


- **Host** runs the full `update()` loop, is the single source of truth
- **Client** skips `update()`, receives state snapshots, interpolates for smooth rendering
- Host has zero input latency, client has ~1 round-trip (mitigated by client-side prediction for own ship)
- All `Math.random()` (modifiers, shield, debuff patterns) only runs on host — no desync risk

## Transport

The DataChannel is opened **unordered** (`{ reliable: false }`). This matters:
an ordered channel makes SCTP hold every newer packet behind a lost one
(head-of-line blocking), so on a lossy link the send queue grows, latency
climbs, and it never recovers — the game gets progressively laggier until the
match ends. Unordered delivery lets fresh snapshots through while a straggler
is still being retransmitted.

The cost of unordered delivery is that packets can arrive out of order, so
**every `state` and `input` message carries a monotonic sequence number `sq`**
and the receiver drops anything not newer than what it has already applied.
Without that guard, a late snapshot would yank positions backwards.

Two more consequences of a lossy/unordered channel:

- **Fire is a counter, not a flag.** `fc` is a monotonic count of shots the
  client has requested; the host fires on any increase. A one-shot boolean
  (the old `fo`) was silently swallowed whenever its packet was dropped or
  reordered.
- **The host drops ticks under backpressure.** `broadcastState()` skips the
  send when `dataChannel.bufferedAmount` exceeds 64KB. Queueing a snapshot is
  pointless — the next one supersedes it — and queueing is exactly how a brief
  hiccup turns into permanent lag.

## ICE / NAT traversal

Signaling goes through the free PeerJS cloud broker. Media/data path uses the
ICE servers in `PEER_OPTS.config.iceServers`.

**PeerJS 1.5.4's built-in ICE defaults are dead.** Its bundled relays
`eu-0.turn.peerjs.com` and `us-0.turn.peerjs.com` no longer resolve at all,
which silently left one Google STUN server as the only option. STUN can only
introduce two peers that are already directly reachable, so any pair needing a
relay — CGNAT, symmetric NAT, mobile data, restrictive office networks — could
never connect, with no error that pointed at the real cause.

The game now sets its own list: three STUN servers, plus whatever is in
`ITB_TURN` (empty by default). **Cross-NAT play needs a real TURN relay in
`ITB_TURN`.** There is no longer a public one usable without credentials —
metered.ca's old open-relay credentials now answer TURN allocate with a 400.
Self-hosted coturn is the path:

```js
const ITB_TURN = [
  { urls: 'turn:turn.example.org:3478', username: '...', credential: '...' },
];
```

Keep the list real — a dead entry adds seconds to ICE gathering on *every*
connection, which is worse than having none. An outright ICE failure is now
detected (`iceconnectionstatechange` → `failed`) and reported as a routing
problem rather than as a bad room code.

## Connection Flow

### Host
1. Click **HOST ONLINE** on title screen
2. PeerJS creates peer with ID `ITB-{4-char-code}` (no ambiguous I/1/O/0)
3. Room code displayed, waiting for opponent (5 min timeout)
4. On incoming connection: send `{t:'start'}`, begin match

### Client
1. Click **JOIN ONLINE**, enter 4-character room code
2. PeerJS connects to `ITB-{CODE}` (30s connection timeout — ICE regularly needs more than 10s)
3. On receiving `start` **or the first `state` snapshot**: set mode to client, begin match
   (`start` can be lost on the unordered channel, which used to hang the joiner on "Starting...")
4. Client uses P1 controls (WASD/mouse/space) mapped to their P2 ship

## Protocol

All messages use short keys to minimize payload size.

### Message Types

| Type | Direction | Fields | Description |
|------|-----------|--------|-------------|
| `start` | Host → Client | `{t:'start'}` | Match begins |
| `state` | Host → Client @ ~45Hz | Full game state (see below) | ~400-600 bytes/tick |
| `input` | Client → Host, on change + 100ms keepalive | `{t,sq,u,d,f,fc,mw,ty}` | Movement + fire input |
| `ping` | Either → Either | `{t:'ping',ts}` | Latency measurement |
| `pong` | Either → Either | `{t:'pong',ts}` | Latency response |

### State Snapshot Format
```js
{
  t: 'state',
  sq: 1234,                // sequence number — receiver drops anything not newer
  gs: 'playing',           // game.state
  ct: 1.5,                 // countdownTimer
  sc: [3, 2],              // scores
  ft: [0, 0.1],            // flashTimers
  rw: -1,                  // roundWinner
  p1: { x, y, w, h, vy, fc, a },  // player 1
  p2: { x, y, w, h, vy, fc, a },  // player 2
  sh: { x, y, vx, vy, l, lt, ls, ct },  // shield
  bl: [{ x, y, vx, vy, o }],  // bullets
  ma: 'blackHole',         // active modifier type
  ann: { text, timer },    // announcement
  gw: { sm, ti, md, is },  // gravity well
  bh: { x, y, ps, bp, ti, md, an },  // black hole
  oc: { fm, ti, md, db, dt, dmd, dp },  // overclock
  sv: [[...], [...]]       // ship variants, resent on the first 25 ticks only
}
```

### Input Format
```js
{
  t: 'input',
  sq: 567,     // sequence number — host drops anything not newer
  u: false,    // up
  d: true,     // down
  f: true,     // fire (held)
  fc: 12,      // monotonic fire count — host fires on any increase
  mw: 0,       // mouseWheelDelta
  ty: null     // touch target Y in native coords, or null
}
```

Sent only when a field changes, plus a 100ms keepalive. The old build sent 60
byte-identical packets a second, which was most of what filled the send queue.

## Client-Side Prediction

The client locally moves its own ship based on input for immediate responsiveness, while the host state corrects the position every tick.

Corrections are smoothed with `smooth(a, b, rate, dt)` — exponential smoothing
that accounts for frame time (`1 - Math.exp(-rate * dt)`), not a flat
per-frame `lerp`. A flat `lerp(a, b, 0.25)` converges four times slower at
30fps than at 120fps, so identical ping felt fine on one machine and laggy on
another.

Bullets and shield are applied directly from host state (no prediction needed — they move fast and aren't player-controlled).

## Disconnect Handling

- Connection close/error → disconnect overlay shown
- Host timeout: 5 min waiting for opponent
- Client timeout: 30s connecting to host
- ICE `failed` → reported as a routing/relay problem, not a bad room code
- A second joiner to an occupied room is refused instead of clobbering the connection
- Win screen in online mode: EXIT only (no REMATCH)
- Tab close: `peer.destroy()` on `beforeunload`

## Latency Display

Ping/pong every 2 seconds, half-RTT displayed in HUD bottom-center during online play.

## Net Modes

The game loop branches on `net.mode`:
- `local`: original behavior, both players on same keyboard
- `host`: runs `update()`, maps `net.remoteInput` to P2, broadcasts state at ~45Hz
- `client`: skips `update()`, applies received state, sends input on change (100ms keepalive), interpolates positions

## Notes

- PeerJS 1.5.4 is bundled locally at `assets/peerjs.min.js` (not loaded from a CDN)
- Arrow/Enter keys disabled in online mode (prevents confusion)
- All modifier randomization runs only on host
- State sync includes full modifier state (gravity well, black hole, overclock + debuff patterns)
