# IN THE BLACK — TODO

## Publisher Info
- Developed & Published by **anarchygames.org**
- Shop link to be added after game is complete

## V1 (Complete) — Core Game
- [x] Two ships, bullets, drifting shield orb
- [x] Shield lock mechanic (2s protection for opponent)
- [x] Shield-player friction (contact affects trajectory)
- [x] Score tracking, first to 6 wins (best of 10)
- [x] Ship grows with each point
- [x] Retro pixel art style with Codex font
- [x] Controls: mouse wheel/W/S/arrows + click/space
- [x] Auto-fire with rate limiter (3.5/sec)
- [x] Color-shifting translucent shield orb

## V2 (Complete) — Match Modifiers
- [x] Gravity Well — alters player movement speed (slow or fast), randomized weight
- [x] Black Hole — pulls players up/down, bends bullet trajectory, can curve shots around locked shield
- [x] Overclock — increases fire rate, post-effect sporadic fire debuff (random burst patterns)
- [x] Randomized modifier weights (intensity varies per spawn)
- [x] Modifier spawn system (random timing during match)

## V3 (Complete) — Cosmetic Ship Upgrades
- [x] 10 tiers of visual ship progression (procedural pixel art)
- [x] Ship tier names: Tin Can → Scout → Interceptor → Viper → Phantom → Wraith → Nova → Supernova → Celestial → LEGENDARY

## V4 (Complete) — Online Multiplayer
- [x] WebRTC P2P via PeerJS (no dedicated server needed)
- [x] Host-authoritative architecture (host runs simulation, client interpolates)
- [x] Lobby: LOCAL PLAY / HOST ONLINE / JOIN ONLINE
- [x] 4-character room codes (no ambiguous I/1/O/0)
- [x] State sync host → client @ 20Hz (~10KB/s)
- [x] Input forwarding client → host @ 60Hz
- [x] Client-side prediction for own ship
- [x] Position interpolation (lerp) for smooth remote rendering
- [x] Full modifier state sync (gravity well, black hole, overclock)
- [x] Ping/pong latency display
- [x] Disconnect detection + overlay
- [x] Arrow/Enter disabled in online mode
- [x] Tab close cleanup (peer.destroy on beforeunload)

## V5 (Complete) — Audio, VFX & Tutorial
- [x] Music system (11 tracks, shuffled playlist)
- [x] SFX: phaser blaster (P1), alternate blaster (P2), explosion, shield impact, thruster loops
- [x] Per-player blaster sounds (P1 original, P2 alternate)
- [x] Explosion particle system (color-coded, 28-40 particles, white flash)
- [x] Bullet particle trails (fading stream behind projectiles)
- [x] P2 color scheme: pink bullets, pink HUD, pink explosions
- [x] Screen shake on hit (decaying intensity, HUD stays stable)
- [x] Ship variants: 3 unique designs per tier (30 total), randomized per match
- [x] Gravity well visual overhaul (screen-edge vignette + drifting particles)
- [x] Black hole: bullets visibly bend, spawns near top/bottom edge
- [x] Tutorial page (tutorial.html) with "HOW TO PLAY" link on title screen

## Future Ideas
- [ ] Spectator mode
- [ ] Leaderboard / stats tracking
- [ ] Dedicated server option for tournament play
