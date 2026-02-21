# Shield Pong — Multiplayer Integration Guide

## Architecture Overview

Shield Pong is designed as a **client-authoritative** game that can be upgraded to **server-authoritative** for cheat prevention. The game state is stored in a single `game` object that can be serialized and synced.

## Lobby System Design

### Flow
1. User in unassigned lobby sees **"Play Shield Pong"** button
2. Clicking creates a **game session** (status: `waiting`)
3. Next user who clicks joins that session (status: `active`)
4. If all existing sessions are `active`, clicking creates a new session
5. Multiple concurrent sessions supported

### Session Object
```json
{
  "sessionId": "uuid",
  "status": "waiting | active | finished",
  "players": ["userId1", "userId2"],
  "createdAt": "timestamp"
}
```

## WebSocket Protocol

### Message Types

#### Client → Server
```json
{ "type": "input", "sessionId": "...", "data": { "up": false, "down": true, "fire": false } }
{ "type": "joinGame" }
{ "type": "leaveGame", "sessionId": "..." }
```

#### Server → Client
```json
{ "type": "matchFound", "sessionId": "...", "playerId": 0 }
{ "type": "waiting", "sessionId": "..." }
{ "type": "state", "sessionId": "...", "data": { /* full game state */ } }
{ "type": "opponentInput", "data": { "up": false, "down": true, "fire": false } }
{ "type": "roundEnd", "scorer": 0, "scores": [3, 2] }
{ "type": "gameOver", "winner": 0, "scores": [10, 7] }
{ "type": "opponentDisconnected" }
```

## Integration Steps

### 1. Replace Input Handling
In the current code, both P1 and P2 are local keyboard inputs. For multiplayer:
- Local player → reads from keyboard/mouse as-is
- Remote player → input comes from WebSocket `opponentInput` messages

```js
// Instead of reading keyboard for P2:
socket.on('message', (msg) => {
  const data = JSON.parse(msg);
  if (data.type === 'opponentInput') {
    input.p2Up = data.data.up;
    input.p2Down = data.data.down;
    input.p2Fire = data.data.fire;
  }
});
```

### 2. Send Local Input
```js
// Every frame, send local input state
function sendInput() {
  socket.send(JSON.stringify({
    type: 'input',
    sessionId: currentSession,
    data: {
      up: input.p1Up,
      down: input.p1Down,
      fire: input.p1Fire
    }
  }));
}
```

### 3. Assign Player Sides
When `matchFound` is received, the `playerId` field tells the client which side they are (0 = left/P1, 1 = right/P2). Remap controls accordingly.

### 4. State Sync (Optional, Server-Authoritative)
For cheat prevention, run the game loop on the server and broadcast the full `game` object to both clients at a fixed tick rate (e.g., 20Hz). Clients interpolate between states for smooth rendering.

```js
// Server sends full state
socket.on('message', (msg) => {
  const data = JSON.parse(msg);
  if (data.type === 'state') {
    Object.assign(game, data.data);
  }
});
```

## Server-Side Session Manager (Pseudocode)

```js
const sessions = new Map();

function handleJoinGame(userId, ws) {
  // Find a waiting session
  let session = [...sessions.values()].find(s => s.status === 'waiting');

  if (session) {
    session.players.push({ id: userId, ws });
    session.status = 'active';
    // Notify both players
    session.players[0].ws.send(JSON.stringify({ type: 'matchFound', sessionId: session.id, playerId: 0 }));
    session.players[1].ws.send(JSON.stringify({ type: 'matchFound', sessionId: session.id, playerId: 1 }));
  } else {
    // Create new session
    session = {
      id: generateId(),
      status: 'waiting',
      players: [{ id: userId, ws }]
    };
    sessions.set(session.id, session);
    ws.send(JSON.stringify({ type: 'waiting', sessionId: session.id }));
  }
}
```

## Notes

- The `game` object is globally accessible — serialize it with `JSON.stringify(game)` for full state sync
- Fire rate, shield speed, and other constants are at the top of the script for easy tuning
- The game uses `requestAnimationFrame` with delta time, so it's frame-rate independent
- Canvas renders at a native 640x400 resolution with integer pixel scaling — looks crisp at any size
- For V2 modifiers (black holes, gravity wells, overclock), the modifier state will be added to the `game` object and synced the same way
