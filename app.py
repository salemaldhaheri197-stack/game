import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🏀 Hoop Shootout Multiplayer", page_icon="🏀", layout="centered")

st.title("🏀 Hoop Shootout — Multiplayer")
st.caption("Up to 5 players over peer-to-peer • Turn-based free throws • Live leaderboard • Mobile friendly")

html_game = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Hoop Shootout Multiplayer</title>
<script src="https://unpkg.com/peerjs@1.5.2/dist/peerjs.min.js"></script>
<style>
    * { box-sizing: border-box; }
    html, body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #0e1117;
        color: #ffffff;
        margin: 0;
        padding: 0;
        -webkit-tap-highlight-color: transparent;
    }
    body {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 8px;
    }
    .app-wrap { width: 100%; max-width: 480px; display: flex; flex-direction: column; align-items: center; }

    .lobby-panel {
        background-color: #16213e;
        padding: 12px 14px;
        border-radius: 10px;
        margin-bottom: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        width: 100%;
    }
    .lobby-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; justify-content: center; }
    .lobby-panel label { font-size: 0.78em; color: #a2a8d3; display: block; margin-bottom: 3px; }
    .lobby-panel input {
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid #0f3460;
        background: #0e1117;
        color: #fff;
        font-size: 0.9em;
        min-width: 0;
    }
    #name-input { width: 130px; }
    #join-id-input { width: 115px; text-transform: uppercase; }
    button {
        padding: 9px 12px;
        background-color: #e94560;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: bold;
        font-size: 0.85em;
        touch-action: manipulation;
    }
    button:hover, button:active { background-color: #0f3460; }
    .start-btn { background-color: #28a745 !important; }
    .start-btn:hover { background-color: #1e7e34 !important; }
    #room-code-box { text-align: center; margin-bottom: 2px; }
    #my-peer-id { color: #00fff5; font-weight: bold; font-size: 1em; letter-spacing: 1px; }
    #copy-btn { padding: 3px 7px; font-size: 0.72em; margin-left: 6px; }
    #status-msg { margin-top: 6px; font-weight: bold; color: #f9d56e; font-size: 0.8em; text-align: center; }
    #player-chips { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 6px; }
    .chip { padding: 2px 8px; border-radius: 10px; font-size: 0.74em; font-weight: bold; color: #0e1117; }

    .canvas-wrap { width: 100%; max-width: 440px; display: flex; justify-content: center; }
    #gameCanvas {
        border: 4px solid #0f3460;
        background-color: #1b2a4a;
        border-radius: 8px;
        display: block;
        width: 100%;
        max-width: 440px;
        height: auto;
        touch-action: none;
    }

    #shoot-btn {
        width: 100%;
        max-width: 440px;
        margin-top: 8px;
        padding: 16px 0;
        font-size: 1.15em;
        background-color: #ff5500;
        border-radius: 10px;
        letter-spacing: 1px;
        text-align: center;
        font-weight: bold;
        touch-action: manipulation;
        user-select: none;
    }
    #shoot-btn.disabled { background-color: #2a2f45; color: #6b7280; cursor: default; }
    #shoot-btn:active:not(.disabled) { background-color: #cc4400; }

    .controls-info { margin-top: 6px; font-size: 0.75em; color: #a2a8d3; text-align: center; max-width: 440px; }

    .boards-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        width: 100%;
        max-width: 440px;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    .board {
        flex: 1;
        min-width: 190px;
        background-color: #16213e;
        border-radius: 8px;
        padding: 8px 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.25);
    }
    .board h3 { margin: 0 0 5px 0; font-size: 0.88em; color: #00fff5; }
    .board-row { display: flex; justify-content: space-between; font-size: 0.8em; padding: 2px 0; border-bottom: 1px solid #0f3460; }
    .board-row:last-child { border-bottom: none; }
    .board-empty { font-size: 0.75em; color: #6b7280; }

    @media (max-width: 400px) {
        .lobby-panel { padding: 9px; }
        #name-input, #join-id-input { width: 95px; font-size: 0.8em; }
        button { padding: 8px 9px; font-size: 0.78em; }
    }
</style>
</head>
<body>
<div class="app-wrap">

    <div class="lobby-panel">
        <div id="room-code-box">
            <span style="font-size:0.78em;color:#a2a8d3;">Your Room Code:</span><br>
            <span id="my-peer-id">Generating...</span>
            <button id="copy-btn" onclick="copyRoomCode()">Copy</button>
        </div>

        <div class="lobby-row">
            <div>
                <label for="name-input">Your name</label>
                <input type="text" id="name-input" placeholder="Baller" maxlength="10" value="Baller">
            </div>
        </div>

        <div class="lobby-row">
            <button class="start-btn" onclick="startSinglePlayer()">▶ Play Solo</button>
            <button onclick="hostMultiplayer()">🌐 Host Room</button>
        </div>
        <div class="lobby-row">
            <input type="text" id="join-id-input" placeholder="ROOM CODE">
            <button onclick="connectToPeer()">Join Room</button>
        </div>
        <div class="lobby-row">
            <button id="start-race-btn" class="start-btn" style="display:none;" onclick="hostStartGame()">🏀 Start Game</button>
        </div>

        <div id="status-msg">Enter your name, then play solo or host/join a P2P room.</div>
        <div id="player-chips"></div>
    </div>

    <div class="canvas-wrap">
        <canvas id="gameCanvas" width="440" height="540"></canvas>
    </div>

    <div id="shoot-btn" class="disabled">🏀 SHOOT</div>

    <div class="controls-info">
        Tap <strong>SHOOT</strong> (or press Space) when the power meter is in the bright zone.
        Too weak = short, too strong = long!
    </div>

    <div class="boards-wrap">
        <div class="board">
            <h3>🏆 Final Results</h3>
            <div id="live-board"><div class="board-empty">Start a game to see scores</div></div>
        </div>
        <div class="board">
            <h3>⭐ Local Best Scores</h3>
            <div id="best-board"><div class="board-empty">No scores yet on this device</div></div>
        </div>
    </div>

</div>

<script>
    // ---------- AUTO-RESIZE THE STREAMLIT IFRAME TO FIT CONTENT (fixes clipped/scrolling layout) ----------
    function reportHeight() {
        const h = document.documentElement.scrollHeight + 12;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: h }, "*");
    }
    window.addEventListener('load', reportHeight);
    window.addEventListener('resize', reportHeight);
    setInterval(reportHeight, 800);
    if (window.ResizeObserver) { new ResizeObserver(reportHeight).observe(document.body); }

    // ---------- SETUP ----------
    const canvas = document.getElementById("gameCanvas");
    const ctx = canvas.getContext("2d");
    const LOGICAL_W = 440, LOGICAL_H = 540;
    const MAX_PLAYERS = 5;
    const PALETTE = ["#00fff5", "#ff00ff", "#ffbe00", "#4dff4d", "#ff6b6b"];

    const shooterX = 95, shooterY = 460;
    const hoopX = 345, hoopY = 100;
    const IDEAL_POWER = 72;               // sweet-spot on the 0-100 power meter
    const hoopFrac = IDEAL_POWER / 100;
    const extendedX = shooterX + (hoopX - shooterX) / hoopFrac;
    const extendedY = shooterY + (hoopY - shooterY) / hoopFrac;

    const TURN_TIME_MS = 6000, FLIGHT_MS = 650, RESULT_HOLD_MS = 850;

    let peer = null, myId = "", myName = "Baller";
    let isOnline = false, isHost = false, connectTimeout = null;
    let connections = {};   // host-only: peerId -> conn
    let hostConn = null;    // client-only

    let players = {};        // id -> {id,name,color,score}
    let turnOrder = [];
    let currentTurnIdx = 0;
    let roundsPerPlayer = 5;
    let shotsTaken = {};

    let matchState = 'lobby'; // lobby | aiming | flying | result | matchOver
    let aimStartTime = 0;
    let meterValue = 0;
    let meterSpeed = 1.4;
    let ball = { t: 0, startTime: 0, landingT: 0, resultText: '', resultColor: '', resultPts: 0, shooterId: null, resultShownAt: 0 };
    let scoreSaved = false;

    function availableColor() {
        const used = Object.values(players).map(p => p.color);
        return PALETTE.find(c => !used.includes(c)) || PALETTE[0];
    }
    function currentName() {
        const v = document.getElementById('name-input').value.trim();
        return v ? v.substring(0, 10) : "Baller";
    }
    function myKey() { return isOnline ? myId : 'me'; }

    function initPeer() {
        const shortId = "HOOP-" + Math.random().toString(36).substring(2, 6).toUpperCase();
        peer = new Peer(shortId, {
            debug: 1,
            config: {
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
                    { urls: 'stun:stun1.l.google.com:19302' },
                    { urls: 'stun:stun2.l.google.com:19302' },
                    { urls: 'stun:stun3.l.google.com:19302' },
                    { urls: 'stun:stun4.l.google.com:19302' },
                    { urls: 'turn:openrelay.metered.ca:80', username: 'openrelayproject', credential: 'openrelayproject' },
                    { urls: 'turn:openrelay.metered.ca:443', username: 'openrelayproject', credential: 'openrelayproject' }
                ]
            }
        });

        peer.on('open', (id) => {
            myId = id;
            document.getElementById('my-peer-id').innerText = id;
            checkAutoJoinFromUrl();
        });

        peer.on('connection', (connection) => {
            if (!isHost) {
                isHost = true;
                isOnline = true;
                registerSelfAsPlayer();
                document.getElementById('start-race-btn').style.display = 'inline-block';
            }
            if (Object.keys(players).length >= MAX_PLAYERS) {
                connection.on('open', () => connection.send({ type: 'room_full' }));
                setTimeout(() => connection.close(), 300);
                return;
            }
            connections[connection.peer] = connection;
            setupHostSideConnection(connection);
        });

        peer.on('error', (err) => {
            if (connectTimeout) clearTimeout(connectTimeout);
            document.getElementById('status-msg').innerText = "⚠️ Network error: " + err.type + ". Check the room code or your connection.";
        });
    }

    function checkAutoJoinFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const room = params.get('room');
        if (room) document.getElementById('join-id-input').value = room.toUpperCase();
    }
    function copyRoomCode() {
        if (!myId) return;
        navigator.clipboard.writeText(myId).then(() => {
            document.getElementById('status-msg').innerText = "📋 Room code copied to clipboard!";
        }).catch(() => {});
    }

    function registerSelfAsPlayer() {
        myName = currentName();
        players[myId] = { id: myId, name: myName, color: PALETTE[0], score: 0 };
    }

    // ---------- SOLO ----------
    function startSinglePlayer() {
        if (connectTimeout) clearTimeout(connectTimeout);
        isOnline = false; isHost = false;
        myName = currentName();
        players = { me: { id: 'me', name: myName, color: PALETTE[0], score: 0 } };
        document.getElementById('start-race-btn').style.display = 'none';
        document.getElementById('status-msg').innerText = "🎮 Solo mode — 10 shots, good luck " + myName + "!";
        beginMatch();
        renderPlayerChips();
        document.activeElement && document.activeElement.blur();
    }

    // ---------- HOST ----------
    function hostMultiplayer() {
        if (!myId) { document.getElementById('status-msg').innerText = "⏳ Generating your room code, try again in a second..."; return; }
        isOnline = true; isHost = true;
        registerSelfAsPlayer();
        matchState = 'lobby';
        document.getElementById('start-race-btn').style.display = 'inline-block';
        document.getElementById('status-msg').innerText = "🌐 Hosting! Share code " + myId + ", then hit Start Game.";
        renderPlayerChips();
    }

    function hostStartGame() {
        if (!isHost) return;
        beginMatch();
        document.getElementById('status-msg').innerText = "🏀 Game on!";
    }

    function beginMatch() {
        roundsPerPlayer = Object.keys(players).length > 1 ? 5 : 10;
        shotsTaken = {};
        Object.keys(players).forEach(id => { shotsTaken[id] = 0; players[id].score = 0; });
        turnOrder = Object.keys(players);
        currentTurnIdx = 0;
        matchState = 'aiming';
        aimStartTime = performance.now();
        meterSpeed = 1.3;
        ball = { t: 0 };
        scoreSaved = false;
        document.getElementById('start-race-btn').innerText = '🏀 Start Game';
        document.getElementById('live-board').innerHTML = '<div class="board-empty">Game in progress...</div>';
    }

    function setupHostSideConnection(conn) {
        conn.on('open', () => {
            const color = availableColor();
            players[conn.peer] = { id: conn.peer, name: 'Baller', color: color, score: 0 };
            if (matchState !== 'lobby') { turnOrder.push(conn.peer); shotsTaken[conn.peer] = 0; }
            document.getElementById('status-msg').innerText = "🟢 A player connected! (" + Object.keys(players).length + "/" + MAX_PLAYERS + ")";
            renderPlayerChips();
        });
        conn.on('data', (data) => {
            const p = players[conn.peer];
            if (!p) return;
            if (data.type === 'client_input' && data.name) p.name = data.name;
            if (data.type === 'shoot') {
                if (matchState === 'aiming' && turnOrder[currentTurnIdx] === conn.peer) resolveShot();
            }
        });
        conn.on('close', () => {
            const idx = turnOrder.indexOf(conn.peer);
            if (idx !== -1) {
                turnOrder.splice(idx, 1);
                if (idx <= currentTurnIdx && currentTurnIdx > 0) currentTurnIdx--;
            }
            delete players[conn.peer];
            delete connections[conn.peer];
            delete shotsTaken[conn.peer];
            renderPlayerChips();
            document.getElementById('status-msg').innerText = "🔴 A player disconnected.";
            if (turnOrder.length === 0) matchState = 'lobby';
        });
    }

    // ---------- CLIENT ----------
    function connectToPeer() {
        const joinId = document.getElementById('join-id-input').value.trim().toUpperCase();
        if (!joinId) return;
        if (joinId === myId) { document.getElementById('status-msg').innerText = "❌ Enter a different player's room code!"; return; }
        if (!myId) { document.getElementById('status-msg').innerText = "⏳ Generating your room code, try again in a second..."; return; }
        myName = currentName();
        document.getElementById('status-msg').innerText = "Connecting to " + joinId + "...";

        hostConn = peer.connect(joinId, { reliable: true });
        isOnline = true; isHost = false;

        if (connectTimeout) clearTimeout(connectTimeout);
        connectTimeout = setTimeout(() => {
            if (!hostConn || !hostConn.open) document.getElementById('status-msg').innerText = "❌ Failed to connect to " + joinId + ". Check the code and try again.";
        }, 8000);

        setupClientSideConnection();
        document.activeElement && document.activeElement.blur();
    }

    function setupClientSideConnection() {
        hostConn.on('open', () => {
            if (connectTimeout) clearTimeout(connectTimeout);
            hostConn.send({ type: 'client_input', name: myName });
            document.getElementById('status-msg').innerText = "🟢 Connected! Waiting for host to start...";
        });
        hostConn.on('data', (data) => {
            if (data.type === 'room_full') { document.getElementById('status-msg').innerText = "❌ Room is full (max " + MAX_PLAYERS + ")."; return; }
            if (data.type === 'host_sync') {
                players = data.players;
                turnOrder = data.turnOrder;
                currentTurnIdx = data.currentTurnIdx;
                roundsPerPlayer = data.roundsPerPlayer;
                shotsTaken = data.shotsTaken;
                matchState = data.matchState;
                meterValue = data.meterValue;
                ball = data.ball;
                renderPlayerChips();
                if (matchState === 'matchOver' && !scoreSaved) {
                    const me = players[myId];
                    if (me) saveBestScore(me.name, me.score);
                    scoreSaved = true;
                }
            }
        });
        hostConn.on('close', () => {
            document.getElementById('status-msg').innerText = "🔴 Lost connection to host.";
            isOnline = false; matchState = 'lobby';
        });
    }

    function renderPlayerChips() {
        const box = document.getElementById('player-chips');
        box.innerHTML = '';
        Object.values(players).forEach(p => {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.style.backgroundColor = p.color;
            chip.innerText = p.name + (p.id === myKey() ? ' (you)' : '');
            box.appendChild(chip);
        });
    }

    // ---------- SHOOTING LOGIC (host authoritative) ----------
    function isMyTurn() { return matchState === 'aiming' && turnOrder[currentTurnIdx] === myKey(); }

    function handleShootPress() {
        if (!isMyTurn()) return;
        if (isHost || !isOnline) {
            resolveShot();
        } else if (hostConn && hostConn.open) {
            hostConn.send({ type: 'shoot' });
        }
    }

    function resolveShot() {
        if (matchState !== 'aiming') return;
        const power = meterValue;
        const diff = Math.abs(power - IDEAL_POWER);
        let pts = 0, text = "MISS", color = "#ff6b6b";
        if (diff <= 4) { pts = 3; text = "SWISH! +3"; color = "#00fff5"; }
        else if (diff <= 9) { pts = 2; text = "SPLASH! +2"; color = "#4dff4d"; }
        else if (diff <= 16) {
            const chance = Math.max(0, (1 - (diff - 9) / 7) * 0.5);
            if (Math.random() < chance) { pts = 2; text = "RATTLED IN! +2"; color = "#4dff4d"; }
            else { text = ["MISS", "OFF THE RIM"][Math.floor(Math.random()*2)]; }
        } else {
            text = ["MISS", "NO GOOD", "AIR BALL"][Math.floor(Math.random()*3)];
        }

        const shooterId = turnOrder[currentTurnIdx];
        const shooter = players[shooterId];
        if (shooter) shooter.score += pts;
        shotsTaken[shooterId] = (shotsTaken[shooterId] || 0) + 1;

        matchState = 'flying';
        ball = { t: 0, startTime: performance.now(), landingT: power / 100, resultText: text, resultColor: color, resultPts: pts, shooterId: shooterId, resultShownAt: 0 };
    }

    function advanceTurn() {
        if (turnOrder.length === 0) { matchState = 'lobby'; return; }
        let attempts = 0;
        do {
            currentTurnIdx = (currentTurnIdx + 1) % turnOrder.length;
            attempts++;
        } while ((shotsTaken[turnOrder[currentTurnIdx]] || 0) >= roundsPerPlayer && attempts <= turnOrder.length);

        const allDone = turnOrder.every(id => (shotsTaken[id] || 0) >= roundsPerPlayer);
        if (allDone) {
            matchState = 'matchOver';
            const me = players[myKey()];
            if (me && !scoreSaved) { saveBestScore(me.name, me.score); scoreSaved = true; }
            document.getElementById('start-race-btn').innerText = '🔁 Play Again';
            document.getElementById('start-race-btn').style.display = (isHost || !isOnline) ? 'inline-block' : 'none';
            renderFinalBoard();
        } else {
            matchState = 'aiming';
            aimStartTime = performance.now();
            const totalShots = Object.values(shotsTaken).reduce((a, b) => a + b, 0);
            meterSpeed = Math.min(3, 1.3 + 0.05 * totalShots);
            ball = { t: 0 };
        }
    }

    // ---------- INPUT ----------
    document.getElementById('shoot-btn').addEventListener('pointerdown', (e) => { e.preventDefault(); handleShootPress(); });
    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') { if (e.key === 'Enter') connectToPeer(); return; }
        if (e.code === 'Space') { e.preventDefault(); handleShootPress(); }
    }, { passive: false });

    // ---------- LOCAL BEST SCORES ----------
    function loadBestScores() {
        try { return JSON.parse(localStorage.getItem('hoopBestScores') || '[]'); } catch (e) { return []; }
    }
    function saveBestScore(name, score) {
        if (score <= 0) return;
        let list = loadBestScores();
        list.push({ name: name, score: score, ts: Date.now() });
        list.sort((a, b) => b.score - a.score);
        list = list.slice(0, 10);
        localStorage.setItem('hoopBestScores', JSON.stringify(list));
        renderBestBoard();
    }
    function renderBestBoard() {
        const box = document.getElementById('best-board');
        const list = loadBestScores();
        if (!list.length) { box.innerHTML = '<div class="board-empty">No scores yet on this device</div>'; return; }
        box.innerHTML = list.map((e, i) => '<div class="board-row"><span>' + (i+1) + '. ' + escapeHtml(e.name) + '</span><span>' + e.score + '</span></div>').join('');
    }
    function renderFinalBoard() {
        const box = document.getElementById('live-board');
        const list = Object.values(players).sort((a, b) => b.score - a.score);
        if (!list.length) { box.innerHTML = '<div class="board-empty">No players</div>'; return; }
        box.innerHTML = list.map((p, i) => '<div class="board-row"><span style="color:' + p.color + '">' + (i+1) + '. ' + escapeHtml(p.name) + '</span><span>' + p.score + '</span></div>').join('');
    }
    function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

    // ---------- DRAWING ----------
    function drawCourt() {
        ctx.fillStyle = "#1b2a4a";
        ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);
        ctx.strokeStyle = "rgba(255,255,255,0.15)";
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(0, 480); ctx.lineTo(LOGICAL_W, 480); ctx.stroke();

        // backboard
        ctx.fillStyle = "#e5e5e5";
        ctx.fillRect(hoopX - 42, hoopY - 68, 84, 10);
        ctx.fillRect(hoopX - 3, hoopY - 68, 6, 55);
        // rim
        ctx.strokeStyle = "#ff5500";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.ellipse(hoopX, hoopY, 26, 8, 0, 0, Math.PI * 2);
        ctx.stroke();
        // net
        ctx.strokeStyle = "rgba(255,255,255,0.5)";
        ctx.lineWidth = 1;
        for (let i = -20; i <= 20; i += 8) {
            ctx.beginPath(); ctx.moveTo(hoopX + i, hoopY + 3); ctx.lineTo(hoopX + i * 0.4, hoopY + 30); ctx.stroke();
        }
    }

    function drawShooter(color, name) {
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(shooterX, shooterY - 30, 12, 0, Math.PI * 2); ctx.fill();
        ctx.fillRect(shooterX - 9, shooterY - 18, 18, 40);
        ctx.font = "bold 12px Arial";
        ctx.textAlign = "center";
        ctx.fillText(name, shooterX, shooterY - 48);
        ctx.textAlign = "left";
    }

    function drawBall(x, y) {
        ctx.fillStyle = "#ff8c00";
        ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#8a4600"; ctx.lineWidth = 1.3;
        ctx.beginPath(); ctx.moveTo(x - 9, y); ctx.lineTo(x + 9, y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x, y + 9); ctx.stroke();
    }

    function drawMeter() {
        const barX = 40, barY = 500, barW = LOGICAL_W - 80, barH = 16;
        ctx.fillStyle = "#0e1117";
        ctx.fillRect(barX, barY, barW, barH);
        const zone = (lo, hi, col) => {
            ctx.fillStyle = col;
            ctx.fillRect(barX + (lo/100)*barW, barY, ((hi-lo)/100)*barW, barH);
        };
        zone(IDEAL_POWER-16, IDEAL_POWER-9, "rgba(255,255,0,0.25)");
        zone(IDEAL_POWER+9, IDEAL_POWER+16, "rgba(255,255,0,0.25)");
        zone(IDEAL_POWER-9, IDEAL_POWER-4, "rgba(77,255,77,0.5)");
        zone(IDEAL_POWER+4, IDEAL_POWER+9, "rgba(77,255,77,0.5)");
        zone(IDEAL_POWER-4, IDEAL_POWER+4, "rgba(0,255,245,0.7)");
        ctx.strokeStyle = "#0f3460"; ctx.lineWidth = 2;
        ctx.strokeRect(barX, barY, barW, barH);
        const ix = barX + (meterValue/100)*barW;
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(ix - 2, barY - 4, 4, barH + 8);
    }

    function currentTurnPlayer() {
        if (!turnOrder.length) return null;
        return players[turnOrder[currentTurnIdx]] || null;
    }

    function updateAndRender() {
        drawCourt();

        if (matchState === 'lobby') {
            ctx.fillStyle = "rgba(0,0,0,0.55)";
            ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);
            ctx.fillStyle = "#00fff5";
            ctx.font = "bold 26px Arial";
            ctx.textAlign = "center";
            ctx.fillText("HOOP SHOOTOUT", LOGICAL_W/2, LOGICAL_H/2 - 10);
            ctx.fillStyle = "#fff";
            ctx.font = "14px Arial";
            ctx.fillText("Play Solo, or Host / Join a room above", LOGICAL_W/2, LOGICAL_H/2 + 18);
            ctx.textAlign = "left";
            document.getElementById('shoot-btn').classList.add('disabled');
            requestAnimationFrame(updateAndRender);
            return;
        }

        if (isHost || !isOnline) {
            if (matchState === 'aiming') {
                meterValue = 50 + 50 * Math.sin((performance.now() - aimStartTime) / 1000 * meterSpeed);
                if (performance.now() - aimStartTime > TURN_TIME_MS) resolveShot();
            } else if (matchState === 'flying') {
                const elapsed = performance.now() - ball.startTime;
                ball.t = Math.min(1, elapsed / FLIGHT_MS);
                if (ball.t >= 1 && !ball.resultShownAt) ball.resultShownAt = performance.now();
                if (ball.resultShownAt && performance.now() - ball.resultShownAt > RESULT_HOLD_MS) advanceTurn();
            }
            if (isOnline) {
                Object.values(connections).forEach(conn => {
                    if (conn.open) conn.send({ type: 'host_sync', players, turnOrder, currentTurnIdx, roundsPerPlayer, shotsTaken, matchState, meterValue, ball });
                });
            }
        }

        const turnPlayer = currentTurnPlayer();

        if (matchState === 'matchOver') {
            ctx.fillStyle = "rgba(0,0,0,0.7)";
            ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);
            ctx.fillStyle = "#ffbe00";
            ctx.font = "bold 26px Arial";
            ctx.textAlign = "center";
            ctx.fillText("GAME OVER", LOGICAL_W/2, 70);
            const ranked = Object.values(players).sort((a,b) => b.score - a.score);
            ctx.font = "bold 16px Arial";
            ranked.slice(0,5).forEach((p, i) => {
                ctx.fillStyle = p.color;
                ctx.fillText((i+1) + ". " + p.name + " — " + p.score + " pts", LOGICAL_W/2, 110 + i*26);
            });
            ctx.fillStyle = "#fff"; ctx.font = "13px Arial";
            ctx.fillText((isHost || !isOnline) ? "Tap Play Again above" : "Waiting for host to restart...", LOGICAL_W/2, LOGICAL_H - 30);
            ctx.textAlign = "left";
            document.getElementById('shoot-btn').classList.add('disabled');
            requestAnimationFrame(updateAndRender);
            return;
        }

        if (turnPlayer) drawShooter(turnPlayer.color, turnPlayer.name + (turnPlayer.id === myKey() ? " (you)" : ""));

        if (matchState === 'aiming') {
            drawMeter();
            drawBall(shooterX, shooterY - 55);
            const secsLeft = Math.max(0, (TURN_TIME_MS - (performance.now() - aimStartTime)) / 1000).toFixed(1);
            ctx.fillStyle = "#f9d56e"; ctx.font = "bold 13px Arial"; ctx.textAlign = "center";
            ctx.fillText("⏱ " + secsLeft + "s", LOGICAL_W/2, 30);
            ctx.textAlign = "left";
        } else if (matchState === 'flying' || matchState === 'result') {
            const t = ball.t;
            const landX = shooterX + (extendedX - shooterX) * ball.landingT;
            const landY = shooterY + (extendedY - shooterY) * ball.landingT;
            const peak = 60 + 140 * ball.landingT;
            const bx = shooterX + (landX - shooterX) * t;
            const by = (shooterY - 55) + (landY - (shooterY - 55)) * t - peak * 4 * t * (1 - t);
            drawBall(bx, by);
            if (ball.resultShownAt) {
                ctx.fillStyle = ball.resultColor;
                ctx.font = "bold 24px Arial";
                ctx.textAlign = "center";
                ctx.fillText(ball.resultText, LOGICAL_W/2, LOGICAL_H/2);
                ctx.textAlign = "left";
            }
        }

        ctx.font = "bold 12px Arial";
        let hy = 22;
        Object.values(players).slice(0, 5).forEach(p => {
            ctx.fillStyle = p.color;
            ctx.fillText(p.name + ": " + p.score, 10, hy);
            hy += 16;
        });

        const shootBtn = document.getElementById('shoot-btn');
        if (isMyTurn()) shootBtn.classList.remove('disabled'); else shootBtn.classList.add('disabled');

        requestAnimationFrame(updateAndRender);
    }

    window.onload = () => {
        initPeer();
        renderBestBoard();
        requestAnimationFrame(updateAndRender);
        reportHeight();
    };
</script>
</body>
</html>
"""

components.html(html_game, height=700, scrolling=False)

st.markdown("""
---
**How multiplayer works:** one player clicks **Host Room** and shares their room code; up to 4 friends
**Join Room** with that code (P2P over STUN/TURN — works across devices and networks, no server needed).
The host is authoritative for the shot simulation and turn order, and relays state to everyone else.

**Leaderboard:** *Final Results* ranks everyone at the end of a match. *Local Best Scores* persists your
top runs on this browser (`localStorage`) — it's per-device, not a shared global leaderboard, since a
real cross-device leaderboard needs a backend/database, which a pure P2P setup can't provide by itself.

**Sizing fix:** the game now reports its actual rendered height back to Streamlit continuously, so the
embedded frame always resizes to fit the content instead of clipping it or forcing an inner scrollbar.
""")
