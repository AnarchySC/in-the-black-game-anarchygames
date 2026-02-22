# IN THE BLACK — Multiplayer Architecture

## Overview

WebRTC peer-to-peer multiplayer using **PeerJS** for signaling. No dedicated game server required. One player hosts (gets a 4-character room code), the other joins with the code.

## Architecture: Host-Authoritative P2P

```
  HOST (P1)                          CLIENT (P2)
  Runs game simulation    <--input-- Sends local input
  Reads local P1 input    --state--> Receives game state
  Sends state @ 20Hz                 Interpolates + renders
            |                              |
            +--- PeerJS DataChannel -------+
                 (signaling via PeerJS cloud)
```

- **Host** runs the full `update()` loop, is the single source of truth
- **Client** skips `update()`, receives state snapshots, interpolates for smooth rendering
- Host has zero input latency, client has ~1 round-trip (mitigated by client-side prediction for own ship)
- All `Math.random()` (modifiers, shield, debuff patterns) only runs on host — no desync risk

## Connection Flow

### Host
1. Click **HOST ONLINE** on title screen
2. PeerJS creates peer with ID `ITB-{4-char-code}` (no ambiguous I/1/O/0)
3. Room code displayed, waiting for opponent (60s timeout)
4. On incoming connection: send `{t:'start'}`, begin match

### Client
1. Click **JOIN ONLINE**, enter 4-character room code
2. PeerJS connects to `ITB-{CODE}` (10s connection timeout)
3. On receiving `start` message: set mode to client, begin match
4. Client uses P1 controls (WASD/mouse/space) mapped to their P2 ship

## Protocol

All messages use short keys to minimize payload size.

### Message Types

| Type | Direction | Fields | Description |
|------|-----------|--------|-------------|
| `start` | Host → Client | `{t:'start'}` | Match begins |
| `state` | Host → Client @ 20Hz | Full game state (see below) | ~400-600 bytes/tick |
| `input` | Client → Host @ 60Hz | `{t,u,d,f,fo,mw}` | Movement + fire input |
| `ping` | Either → Either | `{t:'ping',ts}` | Latency measurement |
| `pong` | Either → Either | `{t:'pong',ts}` | Latency response |

### State Snapshot Format
```js
{
  t: 'state',
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
  oc: { fm, ti, md, db, dt, dmd, dp }  // overclock
}
```

### Input Format
```js
{
  t: 'input',
  u: false,    // up
  d: true,     // down
  f: true,     // fire (held)
  fo: false,   // fire once (single shot)
  mw: 0        // mouseWheelDelta
}
```

## Client-Side Prediction

The client locally moves its own ship based on input for immediate responsiveness, while the host state corrects the position every tick. Interpolation (`lerp`) smooths the correction.

Bullets and shield are applied directly from host state (no prediction needed — they move fast and aren't player-controlled).

## Disconnect Handling

- Connection close/error → disconnect overlay shown
- Host timeout: 60s waiting for opponent
- Client timeout: 10s connecting to host
- Win screen in online mode: EXIT only (no REMATCH)
- Tab close: `peer.destroy()` on `beforeunload`

## Latency Display

Ping/pong every 2 seconds, half-RTT displayed in HUD bottom-center during online play.

## Net Modes

The game loop branches on `net.mode`:
- `local`: original behavior, both players on same keyboard
- `host`: runs `update()`, maps `net.remoteInput` to P2, broadcasts state at 20Hz
- `client`: skips `update()`, applies received state, sends input at 60Hz, interpolates positions

## Notes

- PeerJS CDN: `https://unpkg.com/[email protected]/dist/peerjs.min.js`
- Arrow/Enter keys disabled in online mode (prevents confusion)
- All modifier randomization runs only on host
- State sync includes full modifier state (gravity well, black hole, overclock + debuff patterns)
