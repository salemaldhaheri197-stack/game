import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🏎️ Python Racer Multiplayer", page_icon="🏎️", layout="centered")

st.title("🏎️ Python Racer — Multiplayer")
st.caption("Up to 5 players over peer-to-peer • Live leaderboard • Works on mobile")

html_game = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Python Racer Multiplayer</title>
<script src="https://unpkg.com/peerjs@1.5.2/dist/peerjs.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #0e1117;
        color: #ffffff;
        display: flex;
        flex-direction: column;
        align-items: center;
        margin: 0;
        padding: 8px;
        overflow-x: hidden;
        -webkit-tap-highlight-color: transparent;
    }
    .app-wrap { width: 100%; max-width: 640px; display: flex; flex-direction: column; align-items: center; }

    .lobby-panel {
        background-color: #16213e;
        padding: 14px 16px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        width: 100%;
    }
    .lobby-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; justify-content: center; }
    .lobby-panel label { font-size: 0.8em; color: #a2a8d3; display: block; margin-bottom: 4px; }
    .lobby-panel input {
        padding: 9px 10px;
        border-radius: 6px;
        border: 1px solid #0f3460;
        background: #0e1117;
        color: #fff;
        font-size: 0.95em;
        min-width: 0;
    }
    #name-input { width: 140px; text-transform: none; }
    #join-id-input { width: 120px; text-transform: uppercase; }
    button {
        padding: 10px 14px;
        background-color: #e94560;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: bold;
        font-size: 0.9em;
        touch-action: manipulation;
    }
    button:hover, button:active { background-color: #0f3460; }
    .start-btn { background-color: #28a745 !important; }
    .start-btn:hover { background-color: #1e7e34 !important; }
    #room-code-box { text-align: center; margin-bottom: 4px; }
    #my-peer-id { color: #00fff5; font-weight: bold; font-size: 1.05em; letter-spacing: 1px; }
    #copy-btn { padding: 4px 8px; font-size: 0.75em; margin-left: 6px; }
    #status-msg { margin-top: 8px; font-weight: bold; color: #f9d56e; font-size: 0.85em; text-align: center; }
    #player-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 8px; }
    .chip { padding: 3px 9px; border-radius: 12px; font-size: 0.78em; font-weight: bold; color: #0e1117; }

    .canvas-wrap { width: 100%; max-width: 600px; display: flex; justify-content: center; }
    #gameCanvas {
        border: 4px solid #0f3460;
        background-color: #2d2d2d;
        border-radius: 8px;
        display: block;
        width: 100%;
        max-width: 600px;
        height: auto;
        touch-action: none;
    }

    .touch-controls {
        display: flex;
        gap: 10px;
        width: 100%;
        max-width: 600px;
        margin-top: 10px;
        justify-content: center;
    }
    .touch-btn {
        flex: 1;
        max-width: 140px;
        padding: 18px 0;
        font-size: 1.6em;
        background-color: #16213e;
        border: 2px solid #0f3460;
        border-radius: 10px;
        user-select: none;
        touch-action: none;
    }
    .touch-btn:active, .touch-btn.pressed { background-color: #e94560; }
    #boost-btn { background-color: #16213e; border-color: #ff5500; }
    #boost-btn:active, #boost-btn.pressed { background-color: #ff5500; }

    .controls-info { margin-top: 8px; font-size: 0.8em; color: #a2a8d3; text-align: center; max-width: 560px; }

    .boards-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        width: 100%;
        max-width: 600px;
        margin-top: 12px;
    }
    .board {
        flex: 1;
        min-width: 220px;
        background-color: #16213e;
        border-radius: 8px;
        padding: 10px 14px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.25);
    }
    .board h3 { margin: 0 0 6px 0; font-size: 0.95em; color: #00fff5; }
    .board-row { display: flex; justify-content: space-between; font-size: 0.85em; padding: 3px 0; border-bottom: 1px solid #0f3460; }
    .board-row:last-child { border-bottom: none; }
    .board-empty { font-size: 0.8em; color: #6b7280; }

    @media (max-width: 420px) {
        .lobby-panel { padding: 10px; }
        #name-input, #join-id-input { width: 105px; font-size: 0.85em; }
        button { padding: 9px 10px; font-size: 0.82em; }
        .touch-btn { font-size: 1.3em; padding: 14px 0; }
    }
</style>
</head>
<body>
<div class="app-wrap">

    <div class="lobby-panel">
        <div id="room-code-box">
            <span style="font-size:0.8em;color:#a2a8d3;">Your Room Code:</span><br>
            <span id="my-peer-id">Generating...</span>
            <button id="copy-btn" onclick="copyRoomCode()">Copy</button>
        </div>

        <div class="lobby-row">
            <div>
                <label for="name-input">Your name</label>
                <input type="text" id="name-input" placeholder="Racer" maxlength="10" value="Racer">
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
            <button id="start-race-btn" class="start-btn" style="display:none;" onclick="hostStartRace()">🏁 Start Race for Everyone</button>
        </div>

        <div id="status-msg">Enter your name, then play solo or host/join a P2P room.</div>
        <div id="player-chips"></div>
    </div>

    <div class="canvas-wrap">
        <canvas id="gameCanvas" width="600" height="700"></canvas>
    </div>

    <div class="touch-controls">
        <div class="touch-btn" id="left-btn">◀</div>
        <div class="touch-btn" id="boost-btn">🚀</div>
        <div class="touch-btn" id="right-btn">▶</div>
    </div>

    <div class="controls-info">
        🕹️ Arrow keys / A-D to steer, Up / W to boost — or use the on-screen buttons on mobile.<br>
        🔄 Tap the screen or press Space to restart after a crash.
    </div>

    <div class="boards-wrap">
        <div class="board">
            <h3>🏁 Live Leaderboard</h3>
            <div id="live-board"><div class="board-empty">Start a race to see scores</div></div>
        </div>
        <div class="board">
            <h3>🏆 Local Best Scores</h3>
            <div id="best-board"><div class="board-empty">No scores yet on this device</div></div>
        </div>
    </div>

</div>

<script>
    const canvas = document.getElementById("gameCanvas");
    const ctx = canvas.getContext("2d");

    const LOGICAL_W = 600, LOGICAL_H = 700;
    const lanes = [70, 185, 300, 415, 530];
    const carWidth = 34, carHeight = 56;
    const MAX_PLAYERS = 5;
    const PALETTE = ["#00fff5", "#ff00ff", "#ffbe00", "#4dff4d", "#ff6b6b"];
    const enemyColors = ["#ff0055", "#ffbe00", "#00ff66"];

    let peer = null;
    let myId = "";
    let myName = "Racer";
    let isOnline = false;
    let isHost = false;
    let connectTimeout = null;

    // Host-only: map of peerId -> DataConnection
    let connections = {};
    // Client-only: connection to host
    let hostConn = null;

    let gameStarted = false;
    let gameOver = false;
    let frameCount = 0;
    let level = 1;
    let scoreSaved = false;

    // players keyed by id ("me" for solo, or peerId for online)
    let players = {};
    let laneAssignment = {}; // id -> lane index
    let colorAssignment = {}; // id -> color

    let enemies = [];
    let coins = [];

    function availableLanes() {
        const used = Object.values(laneAssignment);
        const free = [];
        for (let i = 0; i < lanes.length; i++) if (!used.includes(i)) free.push(i);
        return free;
    }
    function availableColor() {
        const used = Object.values(colorAssignment);
        return PALETTE.find(c => !used.includes(c)) || PALETTE[0];
    }

    function initPeer() {
        const shortId = "RACE-" + Math.random().toString(36).substring(2, 6).toUpperCase();
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

        // Host receives incoming connections here
        peer.on('connection', (connection) => {
            if (!isHost) {
                // Not hosting yet -- become host implicitly if someone connects
                isHost = true;
                isOnline = true;
                registerSelfAsPlayer();
                document.getElementById('start-race-btn').style.display = 'inline-block';
            }
            const ids = availableLanes();
            if (Object.keys(players).length >= MAX_PLAYERS || ids.length === 0) {
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

    function currentName() {
        const v = document.getElementById('name-input').value.trim();
        return v ? v.substring(0, 10) : "Racer";
    }

    function registerSelfAsPlayer() {
        myName = currentName();
        laneAssignment[myId] = 2; // host takes center lane
        colorAssignment[myId] = PALETTE[0];
        players[myId] = { id: myId, name: myName, lane: 2, y: 580, color: PALETTE[0], score: 0, alive: true, boosting: false };
    }

    // ---------- SOLO MODE ----------
    function startSinglePlayer() {
        if (connectTimeout) clearTimeout(connectTimeout);
        isOnline = false;
        isHost = false;
        myName = currentName();
        document.getElementById('status-msg').innerText = "🎮 Solo mode — good luck, " + myName + "!";
        document.getElementById('start-race-btn').style.display = 'none';
        players = { me: { id: 'me', name: myName, lane: 2, y: 580, color: PALETTE[0], score: 0, alive: true, boosting: false } };
        resetRoundState();
        gameStarted = true;
        scoreSaved = false;
        document.activeElement && document.activeElement.blur();
    }

    // ---------- HOST MODE ----------
    function hostMultiplayer() {
        if (!myId) {
            document.getElementById('status-msg').innerText = "⏳ Still generating your room code, try again in a second...";
            return;
        }
        isOnline = true;
        isHost = true;
        laneAssignment = {};
        colorAssignment = {};
        registerSelfAsPlayer();
        gameStarted = false;
        gameOver = false;
        document.getElementById('start-race-btn').style.display = 'inline-block';
        document.getElementById('status-msg').innerText = "🌐 Hosting! Share code " + myId + " with friends, then hit Start Race.";
        renderPlayerChips();
    }

    function hostStartRace() {
        if (!isHost) return;
        resetRoundState();
        gameStarted = true;
        scoreSaved = false;
        document.getElementById('status-msg').innerText = "🏁 Race started!";
    }

    function setupHostSideConnection(conn) {
        conn.on('open', () => {
            const freeLanes = availableLanes();
            const lane = freeLanes.length ? freeLanes[0] : 0;
            const color = availableColor();
            laneAssignment[conn.peer] = lane;
            colorAssignment[conn.peer] = color;
            players[conn.peer] = { id: conn.peer, name: 'Racer', lane: lane, y: 580, color: color, score: 0, alive: true, boosting: false };
            document.getElementById('status-msg').innerText = "🟢 A player connected! (" + Object.keys(players).length + "/" + MAX_PLAYERS + ")";
            renderPlayerChips();
        });

        conn.on('data', (data) => {
            const p = players[conn.peer];
            if (!p) return;
            if (data.type === 'client_input') {
                p.lane = data.lane;
                p.boosting = data.boosting;
                if (data.name) p.name = data.name;
            }
        });

        conn.on('close', () => {
            delete players[conn.peer];
            delete connections[conn.peer];
            delete laneAssignment[conn.peer];
            delete colorAssignment[conn.peer];
            renderPlayerChips();
            document.getElementById('status-msg').innerText = "🔴 A player disconnected.";
        });
    }

    // ---------- CLIENT MODE ----------
    function connectToPeer() {
        const joinId = document.getElementById('join-id-input').value.trim().toUpperCase();
        if (!joinId) return;
        if (joinId === myId) {
            document.getElementById('status-msg').innerText = "❌ Enter a different player's room code!";
            return;
        }
        if (!myId) {
            document.getElementById('status-msg').innerText = "⏳ Still generating your room code, try again in a second...";
            return;
        }
        myName = currentName();
        document.getElementById('status-msg').innerText = "Connecting to " + joinId + "...";

        hostConn = peer.connect(joinId, { reliable: true });
        isOnline = true;
        isHost = false;

        if (connectTimeout) clearTimeout(connectTimeout);
        connectTimeout = setTimeout(() => {
            if (!hostConn || !hostConn.open) {
                document.getElementById('status-msg').innerText = "❌ Failed to connect to " + joinId + ". Check the code and try again.";
            }
        }, 8000);

        setupClientSideConnection();
        document.activeElement && document.activeElement.blur();
    }

    function setupClientSideConnection() {
        hostConn.on('open', () => {
            if (connectTimeout) clearTimeout(connectTimeout);
            hostConn.send({ type: 'client_input', lane: 2, boosting: false, name: myName });
            document.getElementById('status-msg').innerText = "🟢 Connected! Waiting for host to start the race...";
            gameStarted = false;
            gameOver = false;
            scoreSaved = false;
        });

        hostConn.on('data', (data) => {
            if (data.type === 'room_full') {
                document.getElementById('status-msg').innerText = "❌ That room is full (max " + MAX_PLAYERS + " players).";
                return;
            }
            if (data.type === 'host_sync') {
                players = data.players;
                enemies = data.enemies;
                coins = data.coins;
                gameOver = data.gameOver;
                gameStarted = data.gameStarted;
                level = data.level;
                renderPlayerChips();
            }
        });

        hostConn.on('close', () => {
            document.getElementById('status-msg').innerText = "🔴 Lost connection to host. Play Solo or join another room.";
            isOnline = false;
            gameStarted = false;
        });
    }

    function sendClientInput() {
        if (isOnline && !isHost && hostConn && hostConn.open) {
            const me = players[myId];
            hostConn.send({ type: 'client_input', lane: me ? me.lane : 2, boosting: me ? me.boosting : false, name: myName });
        }
    }

    function renderPlayerChips() {
        const box = document.getElementById('player-chips');
        box.innerHTML = '';
        Object.values(players).forEach(p => {
            const chip = document.createElement('span');
            chip.className = 'chip';
            chip.style.backgroundColor = p.color;
            chip.innerText = p.name + (p.id === myId ? ' (you)' : '');
            box.appendChild(chip);
        });
    }

    // ---------- GAME STATE ----------
    function resetRoundState() {
        enemies = [];
        coins = [];
        gameOver = false;
        frameCount = 0;
        level = 1;
        Object.values(players).forEach(p => {
            p.y = 580;
            p.score = 0;
            p.alive = true;
            p.boosting = false;
        });
    }

    function restartAfterCrash() {
        if (!gameOver) return;
        if (!isOnline) {
            resetRoundState();
            gameStarted = true;
            scoreSaved = false;
        } else if (isHost) {
            resetRoundState();
            gameStarted = true;
            scoreSaved = false;
        }
        // clients wait for host to restart via next host_sync
    }

    // ---------- INPUT ----------
    function handleSteer(dir) {
        const p = players[isOnline ? (isHost ? myId : myId) : 'me'];
        if (!gameStarted || gameOver || !p || !p.alive) return;
        if (dir === 'left' && p.lane > 0) p.lane--;
        if (dir === 'right' && p.lane < lanes.length - 1) p.lane++;
        sendClientInput();
    }
    function setBoost(state) {
        const p = players[isOnline ? myId : 'me'];
        if (!gameStarted || !p) return;
        p.boosting = state;
        sendClientInput();
    }

    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') { if (e.key === 'Enter') connectToPeer(); return; }
        if (["ArrowUp","ArrowDown","ArrowLeft","ArrowRight","Space","KeyW","KeyA","KeyS","KeyD"].includes(e.code)) e.preventDefault();
        if (e.code === "Space" && gameOver) { restartAfterCrash(); return; }
        if (e.repeat) return;
        if (e.code === "ArrowLeft" || e.code === "KeyA") handleSteer('left');
        if (e.code === "ArrowRight" || e.code === "KeyD") handleSteer('right');
        if (e.code === "ArrowUp" || e.code === "KeyW") setBoost(true);
    }, { passive: false });

    window.addEventListener('keyup', (e) => {
        if (e.target.tagName === 'INPUT') return;
        if (e.code === "ArrowUp" || e.code === "KeyW") setBoost(false);
    }, { passive: false });

    function bindTouchBtn(el, onDown, onUp) {
        const down = (ev) => { ev.preventDefault(); el.classList.add('pressed'); onDown(); };
        const up = (ev) => { ev.preventDefault(); el.classList.remove('pressed'); if (onUp) onUp(); };
        el.addEventListener('pointerdown', down);
        el.addEventListener('pointerup', up);
        el.addEventListener('pointerleave', up);
        el.addEventListener('pointercancel', up);
    }
    bindTouchBtn(document.getElementById('left-btn'), () => handleSteer('left'));
    bindTouchBtn(document.getElementById('right-btn'), () => handleSteer('right'));
    bindTouchBtn(document.getElementById('boost-btn'), () => setBoost(true), () => setBoost(false));
    canvas.addEventListener('pointerdown', () => { if (gameOver) restartAfterCrash(); });

    // ---------- LOCAL BEST SCORES (per-browser leaderboard) ----------
    function loadBestScores() {
        try { return JSON.parse(localStorage.getItem('racerBestScores') || '[]'); }
        catch (e) { return []; }
    }
    function saveBestScore(name, score) {
        if (score <= 0) return;
        let list = loadBestScores();
        list.push({ name: name, score: score, ts: Date.now() });
        list.sort((a, b) => b.score - a.score);
        list = list.slice(0, 10);
        localStorage.setItem('racerBestScores', JSON.stringify(list));
        renderBestBoard();
    }
    function renderBestBoard() {
        const box = document.getElementById('best-board');
        const list = loadBestScores();
        if (!list.length) { box.innerHTML = '<div class="board-empty">No scores yet on this device</div>'; return; }
        box.innerHTML = list.map((e, i) =>
            '<div class="board-row"><span>' + (i+1) + '. ' + escapeHtml(e.name) + '</span><span>' + e.score + '</span></div>'
        ).join('');
    }
    function renderLiveBoard() {
        const box = document.getElementById('live-board');
        const list = Object.values(players).sort((a, b) => b.score - a.score);
        if (!list.length || !gameStarted) { box.innerHTML = '<div class="board-empty">Start a race to see scores</div>'; return; }
        box.innerHTML = list.map((p, i) =>
            '<div class="board-row"><span style="color:' + p.color + '">' + (i+1) + '. ' + escapeHtml(p.name) + (p.alive ? '' : ' 💥') + '</span><span>' + p.score + '</span></div>'
        ).join('');
    }
    function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

    // ---------- DRAWING ----------
    function drawCar(x, y, bodyColor, boosting) {
        const leftX = x - carWidth / 2;
        ctx.fillStyle = "#111111";
        ctx.fillRect(leftX - 3, y + 8, 4, 12);
        ctx.fillRect(leftX + carWidth - 1, y + 8, 4, 12);
        ctx.fillRect(leftX - 3, y + 38, 4, 12);
        ctx.fillRect(leftX + carWidth - 1, y + 38, 4, 12);
        if (boosting) {
            ctx.fillStyle = "#ff5500";
            ctx.beginPath();
            ctx.moveTo(leftX + 8, y + carHeight);
            ctx.lineTo(leftX + carWidth / 2, y + carHeight + Math.random() * 10 + 15);
            ctx.lineTo(leftX + carWidth - 8, y + carHeight);
            ctx.fill();
        }
        ctx.fillStyle = bodyColor;
        ctx.fillRect(leftX, y, carWidth, carHeight);
        ctx.fillStyle = "#1a1a1a";
        ctx.fillRect(leftX + 4, y + 12, carWidth - 8, 18);
        ctx.fillStyle = bodyColor;
        ctx.fillRect(leftX + 6, y + 16, carWidth - 12, 9);
    }

    function drawCoin(x, y) {
        ctx.fillStyle = "#ffd700";
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#b8860b";
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    function updateAndRender() {
        ctx.fillStyle = "#2d2d2d";
        ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);

        ctx.strokeStyle = "#ffffff";
        ctx.setLineDash([20, 15]);
        ctx.beginPath();
        [127, 242, 357, 472].forEach(x => { ctx.moveTo(x, 0); ctx.lineTo(x, LOGICAL_H); });
        ctx.stroke();
        ctx.setLineDash([]);

        if (!gameStarted) {
            ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
            ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);
            ctx.fillStyle = "#00fff5";
            ctx.font = "bold 30px Arial";
            ctx.textAlign = "center";
            ctx.fillText("PYTHON RACER", LOGICAL_W / 2, LOGICAL_H / 2 - 20);
            ctx.fillStyle = "#ffffff";
            ctx.font = "15px Arial";
            ctx.fillText("Play Solo, or Host / Join a P2P room above", LOGICAL_W / 2, LOGICAL_H / 2 + 15);
            ctx.textAlign = "left";
            requestAnimationFrame(updateAndRender);
            return;
        }

        if (!isOnline || isHost) {
            if (!gameOver) {
                const alivePlayers = Object.values(players).filter(p => p.alive);
                const maxScore = Math.max(0, ...Object.values(players).map(p => p.score));
                level = Math.floor(maxScore / 100) + 1;
                const baseSpeed = 5 + (level * 1.1);
                const anyBoost = alivePlayers.some(p => p.boosting);
                const speed = baseSpeed * (anyBoost ? 1.6 : 1.0);

                frameCount++;
                if (frameCount % Math.max(16, 40 - level * 2) === 0) {
                    enemies.push({ x: lanes[Math.floor(Math.random() * lanes.length)], y: -60, color: enemyColors[Math.floor(Math.random() * enemyColors.length)] });
                }
                if (frameCount % 85 === 0) {
                    coins.push({ x: lanes[Math.floor(Math.random() * lanes.length)], y: -30 });
                }

                for (let i = coins.length - 1; i >= 0; i--) {
                    coins[i].y += speed;
                    Object.values(players).forEach(p => {
                        if (p.alive && Math.abs(lanes[p.lane] - coins[i].x) < 25 && Math.abs(p.y - coins[i].y) < 30) {
                            p.score += 25;
                            coins.splice(i, 1);
                        }
                    });
                    if (coins[i] && coins[i].y > LOGICAL_H + 40) coins.splice(i, 1);
                }

                for (let i = enemies.length - 1; i >= 0; i--) {
                    enemies[i].y += speed;
                    Object.values(players).forEach(p => {
                        if (p.alive && Math.abs(lanes[p.lane] - enemies[i].x) < 26 && Math.abs(p.y - enemies[i].y) < 45) {
                            p.alive = false;
                        }
                    });
                    if (enemies[i] && enemies[i].y > LOGICAL_H + 20) {
                        enemies.splice(i, 1);
                        Object.values(players).forEach(p => { if (p.alive) p.score += p.boosting ? 20 : 10; });
                    }
                }

                if (Object.values(players).length && Object.values(players).every(p => !p.alive)) gameOver = true;

                if (isOnline) {
                    Object.values(connections).forEach(conn => {
                        if (conn.open) {
                            conn.send({ type: 'host_sync', players: players, enemies: enemies, coins: coins, gameOver: gameOver, gameStarted: gameStarted, level: level });
                        }
                    });
                }
            }
        }

        coins.forEach(c => drawCoin(c.x, c.y));
        enemies.forEach(e => drawCar(e.x, e.y, e.color, false));
        Object.values(players).forEach(p => { if (p.alive) drawCar(lanes[p.lane], p.y, p.color, p.boosting); });

        ctx.font = "bold 13px Arial";
        let hy = 22;
        Object.values(players).slice(0, 5).forEach((p, i) => {
            ctx.fillStyle = p.color;
            ctx.fillText(p.name + ": " + p.score, 12, hy);
            hy += 18;
        });

        if (gameOver) {
            ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
            ctx.fillRect(0, 0, LOGICAL_W, LOGICAL_H);
            ctx.fillStyle = "#ff0055";
            ctx.font = "bold 28px Arial";
            ctx.textAlign = "center";
            ctx.fillText("CRASHED", LOGICAL_W / 2, LOGICAL_H / 2 - 10);
            ctx.fillStyle = "#ffffff";
            ctx.font = "16px Arial";
            ctx.fillText(isHost || !isOnline ? "Press SPACE or tap to restart" : "Waiting for host to restart...", LOGICAL_W / 2, LOGICAL_H / 2 + 25);
            ctx.textAlign = "left";

            if (!scoreSaved) {
                const me = players[isOnline ? myId : 'me'];
                if (me) { saveBestScore(me.name, me.score); }
                scoreSaved = true;
            }
        }

        renderLiveBoard();
        requestAnimationFrame(updateAndRender);
    }

    window.onload = () => {
        initPeer();
        renderBestBoard();
        requestAnimationFrame(updateAndRender);
    };
</script>
</body>
</html>
"""

components.html(html_game, height=1150, scrolling=True)

st.markdown("""
---
**How multiplayer works:** one player clicks **Host Room** and shares their room code; up to 4 friends
**Join Room** with that code (works across devices/networks via P2P + STUN/TURN, same as before).
The host's browser is authoritative for game logic and relays state to everyone else — no external
server or database is required.

**About the leaderboard:** the *Live Leaderboard* shows everyone's score during the current race.
The *Local Best Scores* board persists your top runs in this browser (via `localStorage`), so it's
per-device rather than a shared global leaderboard — a truly global leaderboard across devices would
need a small backend/database, which is outside what a pure P2P setup can do.
""")
