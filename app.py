import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🏎️ Python Racer", page_icon="🏎️", layout="centered")

st.title("🏎️ Python Racer")

html_game = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Racer</title>
    <!-- PeerJS for P2P -->
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
            overflow: hidden;
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
            width: 130px;
            text-transform: uppercase;
        }
        .lobby-panel button {
            padding: 8px 12px;
            background-color: #e94560;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .lobby-panel button:hover { background-color: #0f3460; }
        .start-btn { background-color: #28a745 !important; font-size: 1.05em; padding: 8px 18px !important; }
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
    </style>
</head>
<body>

    <!-- Lobby Section -->
    <div class="lobby-panel">
        <div>
            <strong>My Online Room Code:</strong> <span id="my-peer-id" style="color: #00fff5;">Generating...</span>
        </div>
        <div style="margin-top: 10px;">
            <button class="start-btn" onclick="startSinglePlayer()">▶ START GAME</button>
            <input type="text" id="join-id-input" placeholder="ROOM CODE" />
            <button onclick="connectToPeer()">Join P2P Room</button>
        </div>
        <div id="status-msg">Click "START GAME" for Single Player, or Join/Share a Code for Online P2P!</div>
    </div>

    <!-- Canvas -->
    <canvas id="gameCanvas" width="500" height="480"></canvas>
    
    <div class="controls-info">
        🕹️ <strong>Controls:</strong> Left / Right Arrows or A / D to steer | Up Arrow or W for Nitro<br>
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
        let connectTimeout = null;

        let gameStarted = false;
        let gameOver = false;
        let frameCount = 0;
        let level = 1;

        let p1 = { lane: 1, y: 400, color: "#00fff5", score: 0, alive: true, boosting: false };
        let p2 = { lane: 2, y: 400, color: "#ff00ff", score: 0, alive: false, boosting: false };

        let enemies = [];
        let coins = [];
        const enemyColors = ["#ff0055", "#ffbe00", "#00ff66"];

        function initPeer() {
            // Standard short uppercase ID setup
            const shortId = "RACE-" + Math.random().toString(36).substring(2, 6).toUpperCase();
            
            // Expanded STUN/TURN server configuration to bypass strict firewalls & NATs
            peer = new Peer(shortId, {
                debug: 1,
                config: {
                    iceServers: [
                        { urls: 'stun:stun.l.google.com:19302' },
                        { urls: 'stun:stun1.l.google.com:19302' },
                        { urls: 'stun:stun2.l.google.com:19302' },
                        { urls: 'stun:stun3.l.google.com:19302' },
                        { urls: 'stun:stun4.l.google.com:19302' },
                        {
                            urls: 'turn:openrelay.metered.ca:80',
                            username: 'openrelayproject',
                            credential: 'openrelayproject'
                        },
                        {
                            urls: 'turn:openrelay.metered.ca:443',
                            username: 'openrelayproject',
                            credential: 'openrelayproject'
                        }
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
                p2.alive = true;
                setupConnection();
            });

            peer.on('error', (err) => {
                if (connectTimeout) clearTimeout(connectTimeout);
                document.getElementById('status-msg').innerText = "⚠️ Network error: " + err.type + ". Check room code or firewall.";
            });
        }

        function startSinglePlayer() {
            if (connectTimeout) clearTimeout(connectTimeout);
            isOnline = false;
            p2.alive = false;
            document.getElementById('status-msg').innerText = "🎮 Playing Single Player Mode";
            resetGameState();
            gameStarted = true;
            document.activeElement.blur();
        }

        function connectToPeer() {
            const joinId = document.getElementById('join-id-input').value.trim().toUpperCase();
            if (!joinId) return;
            if (joinId === myId) {
                document.getElementById('status-msg').innerText = "❌ Enter a different player's Room Code!";
                return;
            }
            
            document.getElementById('status-msg').innerText = "Connecting to " + joinId + "...";
            
            // Reliable connection call with reliable state option
            conn = peer.connect(joinId, { reliable: true });
            isOnline = true;
            isHost = false;
            p2.alive = true;

            // Timeout check if peer is unreachable
            if (connectTimeout) clearTimeout(connectTimeout);
            connectTimeout = setTimeout(() => {
                if (!conn || !conn.open) {
                    document.getElementById('status-msg').innerText = "❌ Failed to connect to " + joinId + ". Ensure Room Code is active and try again.";
                }
            }, 8000);

            setupConnection();
            document.activeElement.blur();
        }

        function setupConnection() {
            conn.on('open', () => {
                if (connectTimeout) clearTimeout(connectTimeout);
                document.getElementById('status-msg').innerText = "🟢 Connected! " + (isHost ? "You are HOST (P1)" : "You are CLIENT (P2)");
                resetGameState();
                gameStarted = true;
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
                    gameStarted = true;
                } else if (data.type === 'restart') {
                    resetGameState();
                    gameStarted = true;
                }
            });

            conn.on('close', () => {
                document.getElementById('status-msg').innerText = "🔴 Connection Lost. Click START GAME for Single Player.";
                isOnline = false;
            });
        }

        function resetGame() {
            resetGameState();
            gameStarted = true;
            if (isOnline && isHost && conn && conn.open) {
                conn.send({ type: 'restart' });
            }
        }

        function resetGameState() {
            p1 = { lane: 1, y: 400, color: "#00fff5", score: 0, alive: true, boosting: false };
            p2 = { lane: 2, y: 400, color: "#ff00ff", score: 0, alive: isOnline, boosting: false };
            enemies = [];
            coins = [];
            gameOver = false;
            frameCount = 0;
            level = 1;
        }

        // Keyboard Event Handlers
        window.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT') {
                if (e.key === 'Enter') {
                    connectToPeer();
                }
                return;
            }

            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", "KeyW", "KeyA", "KeyS", "KeyD"].includes(e.code)) {
                e.preventDefault();
            }

            if (e.code === "Space" && gameOver) {
                resetGame();
                return;
            }

            let myP = (!isOnline || isHost) ? p1 : p2;

            if (gameStarted && myP.alive && !gameOver) {
                let moved = false;
                if ((e.code === "ArrowLeft" || e.code === "KeyA") && myP.lane > 0) { myP.lane--; moved = true; }
                if ((e.code === "ArrowRight" || e.code === "KeyD") && myP.lane < lanes.length - 1) { myP.lane++; moved = true; }
                if (e.code === "ArrowUp" || e.code === "KeyW") { myP.boosting = true; moved = true; }

                if (moved && isOnline && !isHost && conn && conn.open) {
                    conn.send({ type: 'client_input', lane: p2.lane, boosting: p2.boosting });
                }
            }
        }, { passive: false });

        window.addEventListener('keyup', (e) => {
            if (e.target.tagName === 'INPUT') return;

            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", "KeyW", "KeyA", "KeyS", "KeyD"].includes(e.code)) {
                e.preventDefault();
            }

            let myP = (!isOnline || isHost) ? p1 : p2;

            if (gameStarted && (e.code === "ArrowUp" || e.code === "KeyW")) {
                myP.boosting = false;
                if (isOnline && !isHost && conn && conn.open) {
                    conn.send({ type: 'client_input', lane: p2.lane, boosting: p2.boosting });
                }
            }
        }, { passive: false });

        function drawCar(x, y, bodyColor, isPlayer = false, boosting = false) {
            const leftX = x - carWidth / 2;

            ctx.fillStyle = "#111111";
            ctx.fillRect(leftX - 3, y + 8, 4, 12);
            ctx.fillRect(leftX + carWidth - 1, y + 8, 4, 12);
            ctx.fillRect(leftX - 3, y + 40, 4, 12);
            ctx.fillRect(leftX + carWidth - 1, y + 40, 4, 12);

            if (isPlayer && boosting) {
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

            if (!gameStarted) {
                // Title Screen Overlay
                ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
                ctx.fillRect(0, 0, 500, 480);
                ctx.fillStyle = "#00fff5";
                ctx.font = "bold 30px Arial";
                ctx.fillText("PYTHON RACER", 130, 210);
                ctx.fillStyle = "#ffffff";
                ctx.font = "16px Arial";
                ctx.fillText("Click 'START GAME' or Join Online Room", 100, 250);
                requestAnimationFrame(updateAndRender);
                return;
            }

            if (!isOnline || isHost) {
                if (!gameOver) {
                    let activePlayers = [p1, p2].filter(p => p.alive);
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
                            if (p2.alive && isOnline) p2.score += p2.boosting ? 20 : 10;
                        }
                    }

                    if (!p1.alive && (!isOnline || !p2.alive)) gameOver = true;

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

            // Draw Entities
            coins.forEach(c => drawCoin(c.x, c.y));
            enemies.forEach(e => drawCar(e.x, e.y, e.color));

            if (p1.alive) drawCar(lanes[p1.lane], p1.y, p1.color, true, p1.boosting);
            if (isOnline && p2.alive) drawCar(lanes[p2.lane], p2.y, p2.color, true, p2.boosting);

            // HUD
            ctx.font = "bold 13px Arial";
            ctx.fillStyle = p1.color;
            ctx.fillText(`P1 Score: ${p1.score}`, 15, 25);

            if (isOnline) {
                ctx.fillStyle = p2.color;
                ctx.fillText(`P2 Score: ${p2.score}`, 380, 25);
            }

            if (gameOver) {
                ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
                ctx.fillRect(0, 0, 500, 480);
                ctx.fillStyle = "#ff0055";
                ctx.font = "bold 28px Arial";
                ctx.fillText(isOnline ? "BOTH PLAYERS CRASHED" : "GAME OVER", isOnline ? 85 : 160, 220);
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