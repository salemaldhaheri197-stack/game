import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🏎️ Multiplayer Python Racer", page_icon="🏎️", layout="centered")

st.title("🏎️ Multiplayer Python Racer")
st.write("Play online with a friend over P2P **OR** share a keyboard locally!")

html_game = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multiplayer Python Racer</title>
    <!-- PeerJS with WebRTC STUN support -->
    <script src="https://unpkg.com/peerjs@1.5.2/dist/peerjs.min.js"></script>

    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0e1117;
            color: #ffffff;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0;
            padding: 5px;
        }
        .lobby-panel {
            background-color: #16213e;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            text-align: center;
            width: 480px;
        }
        .lobby-panel input {
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #0f3460;
            margin-right: 5px;
            width: 140px;
            text-transform: uppercase;
        }
        .lobby-panel button {
            padding: 8px 14px;
            background-color: #e94560;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .lobby-panel button:hover { background-color: #0f3460; }
        #status-msg { margin-top: 8px; font-weight: bold; color: #f9d56e; font-size: 0.9em; }
        
        #gameCanvas {
            border: 4px solid #0f3460;
            background-color: #2d2d2d;
            border-radius: 8px;
            display: block;
        }
        .controls-info {
            margin-top: 10px;
            font-size: 0.85em;
            color: #a2a8d3;
            text-align: center;
            max-width: 500px;
        }
        .mode-btn {
            background-color: #0f3460 !important;
            margin-left: 5px;
        }
    </style>
</head>
<body>

    <!-- Lobby Section -->
    <div class="lobby-panel">
        <div>
            <strong>My Room Code:</strong> <span id="my-peer-id" style="color: #00fff5;">Generating...</span>
        </div>
        <div style="margin-top: 10px;">
            <input type="text" id="join-id-input" placeholder="ROOM CODE" />
            <button onclick="connectToPeer()">Join Online Room</button>
            <button class="mode-btn" onclick="startLocalMode()">Local 2P Mode</button>
        </div>
        <div id="status-msg">Share your Code with Player 2 or click "Local 2P Mode" to play on 1 keyboard!</div>
    </div>

    <!-- Canvas -->
    <canvas id="gameCanvas" width="500" height="480"></canvas>
    
    <div class="controls-info">
        🩵 <strong>P1 (Host / Left):</strong> A / D to steer | W for Nitro<br>
        🩷 <strong>P2 (Client / Right):</strong> Left / Right Arrows to steer | Up Arrow for Nitro<br>
        🔄 <strong>Spacebar:</strong> Restart Game
    </div>

    <script>
        const canvas = document.getElementById("gameCanvas");
        const ctx = canvas.getContext("2d");

        const lanes = [70, 180, 310, 420];
        const carWidth = 34;
        const carHeight = 58;

        let peer = null;
        let conn = null;
        let myId = "";
        let isOnline = false;
        let isHost = true;

        let keys = {};
        let frameCount = 0;
        let level = 1;
        let gameOver = false;

        let p1 = { lane: 1, y: 400, color: "#00fff5", score: 0, alive: true, boosting: false };
        let p2 = { lane: 2, y: 400, color: "#ff00ff", score: 0, alive: true, boosting: false };

        let enemies = [];
        let coins = [];
        const enemyColors = ["#ff0055", "#ffbe00", "#00ff66"];

        // Initialize PeerJS with public STUN servers for reliable cross-network connection
        function initPeer() {
            const shortId = Math.random().toString(36).substring(2, 7).toUpperCase();
            peer = new Peer(shortId, {
                config: {
                    iceServers: [
                        { urls: 'stun:stun.l.google.com:19302' },
                        { urls: 'stun:stun1.l.google.com:19302' }
                    ]
                }
            });

            peer.on('open', (id) => {
                myId = id;
                document.getElementById('my-peer-id').innerText = id;
            });

            peer.on('connection', (connection) => {
                conn = connection;
                isOnline = true;
                isHost = true;
                setupConnection();
            });

            peer.on('error', (err) => {
                document.getElementById('status-msg').innerText = "⚠️ Network alert: " + err.type;
            });
        }

        function startLocalMode() {
            isOnline = false;
            document.getElementById('status-msg').innerText = "🎮 Playing in Local 2-Player Mode (Shared Keyboard)";
            resetGame();
        }

        function connectToPeer() {
            const joinId = document.getElementById('join-id-input').value.trim().toUpperCase();
            if (!joinId) return;
            if (joinId === myId) {
                document.getElementById('status-msg').innerText = "❌ Enter a different player's Room Code!";
                return;
            }
            
            document.getElementById('status-msg').innerText = "Connecting to " + joinId + "...";
            conn = peer.connect(joinId);
            isOnline = true;
            isHost = false;
            setupConnection();
        }

        function setupConnection() {
            conn.on('open', () => {
                document.getElementById('status-msg').innerText = "🟢 Connected Online! " + (isHost ? "You are HOST (P1)" : "You are CLIENT (P2)");
                resetGame();
            });

            conn.on('data', (data) => {
                if (data.type === 'client_input') {
                    p2.lane = data.lane;
                    p2.boosting = data.boosting;
                } else if (data.type === 'host_sync') {
                    enemies = data.enemies;
                    coins = data.coins;
                    gameOver = data.gameOver;
                    p1 = data.p1;
                    p2 = data.p2;
                } else if (data.type === 'restart') {
                    resetGameState();
                }
            });

            conn.on('close', () => {
                document.getElementById('status-msg').innerText = "🔴 Connection Lost. Switched to Local Mode.";
                isOnline = false;
            });
        }

        function resetGame() {
            resetGameState();
            if (isOnline && isHost) {
                conn.send({ type: 'restart' });
            }
        }

        function resetGameState() {
            p1 = { lane: 1, y: 400, color: "#00fff5", score: 0, alive: true, boosting: false };
            p2 = { lane: 2, y: 400, color: "#ff00ff", score: 0, alive: true, boosting: false };
            enemies = [];
            coins = [];
            gameOver = false;
            frameCount = 0;
            level = 1;
        }

        // Controls
        window.addEventListener('keydown', (e) => {
            if (e.code === "Space" && gameOver) {
                resetGame();
                return;
            }

            if (!isOnline) {
                // Local mode handling
                if (p1.alive && !gameOver) {
                    if ((e.key === 'a' || e.key === 'A') && p1.lane > 0) p1.lane--;
                    if ((e.key === 'd' || e.key === 'D') && p1.lane < lanes.length - 1) p1.lane++;
                    if (e.key === 'w' || e.key === 'W') p1.boosting = true;
                }
                if (p2.alive && !gameOver) {
                    if (e.key === 'ArrowLeft' && p2.lane > 0) p2.lane--;
                    if (e.key === 'ArrowRight' && p2.lane < lanes.length - 1) p2.lane++;
                    if (e.key === 'ArrowUp') p2.boosting = true;
                }
            } else {
                // Online P2P mode handling
                let myP = isHost ? p1 : p2;
                let moved = false;

                if (myP.alive && !gameOver) {
                    if ((e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') && myP.lane > 0) { myP.lane--; moved = true; }
                    if ((e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') && myP.lane < lanes.length - 1) { myP.lane++; moved = true; }
                    if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') { myP.boosting = true; moved = true; }

                    if (moved && !isHost && conn && conn.open) {
                        conn.send({ type: 'client_input', lane: p2.lane, boosting: p2.boosting });
                    }
                }
            }
        });

        window.addEventListener('keyup', (e) => {
            if (!isOnline) {
                if (e.key === 'w' || e.key === 'W') p1.boosting = false;
                if (e.key === 'ArrowUp') p2.boosting = false;
            } else {
                let myP = isHost ? p1 : p2;
                if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') {
                    myP.boosting = false;
                    if (!isHost && conn && conn.open) {
                        conn.send({ type: 'client_input', lane: p2.lane, boosting: p2.boosting });
                    }
                }
            }
        });

        function drawCar(x, y, bodyColor, isPlayer = false, boosting = false) {
            const leftX = x - carWidth / 2;

            // Wheels
            ctx.fillStyle = "#111111";
            ctx.fillRect(leftX - 3, y + 8, 4, 12);
            ctx.fillRect(leftX + carWidth - 1, y + 8, 4, 12);
            ctx.fillRect(leftX - 3, y + 40, 4, 12);
            ctx.fillRect(leftX + carWidth - 1, y + 40, 4, 12);

            // Boost Flame
            if (isPlayer && boosting) {
                ctx.fillStyle = "#ff5500";
                ctx.beginPath();
                ctx.moveTo(leftX + 8, y + carHeight);
                ctx.lineTo(leftX + carWidth / 2, y + carHeight + Math.random() * 10 + 15);
                ctx.lineTo(leftX + carWidth - 8, y + carHeight);
                ctx.fill();
            }

            // Body
            ctx.fillStyle = bodyColor;
            ctx.fillRect(leftX, y, carWidth, carHeight);

            // Roof
            ctx.fillStyle = "#1a1a1a";
            ctx.fillRect(leftX + 4, y + 14, carWidth - 8, 20);
            ctx.fillStyle = bodyColor;
            ctx.fillRect(leftX + 6, y + 18, carWidth - 12, 10);
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
            // Physics loop runs on Host or in Local Mode
            if (!isOnline || isHost) {
                if (!gameOver) {
                    let maxScore = Math.max(p1.score, p2.score);
                    level = Math.floor(maxScore / 100) + 1;
                    let baseSpeed = 5 + (level * 1.1);

                    let anyBoost = (p1.alive && p1.boosting) || (p2.alive && p2.boosting);
                    let speed = baseSpeed * (anyBoost ? 1.6 : 1.0);

                    frameCount++;
                    if (frameCount % Math.max(16, 40 - level * 2) === 0) {
                        enemies.push({
                            x: lanes[Math.floor(Math.random() * lanes.length)],
                            y: -60,
                            color: enemyColors[Math.floor(Math.random() * enemyColors.length)]
                        });
                    }

                    if (frameCount % 85 === 0) {
                        coins.push({
                            x: lanes[Math.floor(Math.random() * lanes.length)],
                            y: -30
                        });
                    }

                    // Move Coins
                    for (let i = coins.length - 1; i >= 0; i--) {
                        coins[i].y += speed;
                        [p1, p2].forEach(p => {
                            if (p.alive && Math.abs(lanes[p.lane] - coins[i].x) < 25 && Math.abs(p.y - coins[i].y) < 30) {
                                p.score += 25;
                                coins.splice(i, 1);
                            }
                        });
                        if (coins[i] && coins[i].y > 520) coins.splice(i, 1);
                    }

                    // Move Enemies
                    for (let i = enemies.length - 1; i >= 0; i--) {
                        enemies[i].y += speed;
                        [p1, p2].forEach(p => {
                            if (p.alive && Math.abs(lanes[p.lane] - enemies[i].x) < 26 && Math.abs(p.y - enemies[i].y) < 45) {
                                p.alive = false;
                            }
                        });

                        if (enemies[i].y > 500) {
                            enemies.splice(i, 1);
                            if (p1.alive) p1.score += p1.boosting ? 20 : 10;
                            if (p2.alive) p2.score += p2.boosting ? 20 : 10;
                        }
                    }

                    if (!p1.alive && !p2.alive) gameOver = true;

                    // Sync state to Client if online
                    if (isOnline && conn && conn.open) {
                        conn.send({
                            type: 'host_sync',
                            enemies: enemies,
                            coins: coins,
                            gameOver: gameOver,
                            p1: p1,
                            p2: p2
                        });
                    }
                }
            }

            // Render
            ctx.fillStyle = "#2d2d2d";
            ctx.fillRect(0, 0, 500, 480);

            // Lane Markings
            ctx.strokeStyle = "#ffffff";
            ctx.setLineDash([20, 15]);
            ctx.beginPath();
            [125, 250, 375].forEach(x => {
                ctx.moveTo(x, 0);
                ctx.lineTo(x, 480);
            });
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw Entities
            coins.forEach(c => drawCoin(c.x, c.y));
            enemies.forEach(e => drawCar(e.x, e.y, e.color));

            if (p1.alive) drawCar(lanes[p1.lane], p1.y, p1.color, true, p1.boosting);
            if (p2.alive) drawCar(lanes[p2.lane], p2.y, p2.color, true, p2.boosting);

            // HUD
            ctx.font = "bold 13px Arial";
            ctx.fillStyle = p1.color;
            ctx.fillText(`P1: ${p1.score} pts`, 15, 25);

            ctx.fillStyle = p2.color;
            ctx.fillText(`P2: ${p2.score} pts`, 380, 25);

            if (gameOver) {
                ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
                ctx.fillRect(0, 0, 500, 480);
                ctx.fillStyle = "#ff0055";
                ctx.font = "bold 28px Arial";
                ctx.fillText("BOTH PLAYERS CRASHED", 85, 220);
                ctx.fillStyle = "#ffffff";
                ctx.font = "16px Arial";
                ctx.fillText("Press SPACEBAR to Restart", 150, 260);
            }

            requestAnimationFrame(updateAndRender);
        }

        window.onload = () => {
            initPeer();
            requestAnimationFrame(updateAndRender);
        };
    </script>
</body>
</html>
"""

components.html(html_game, height=680, scrolling=False)