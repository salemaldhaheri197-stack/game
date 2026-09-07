import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="P2P Multiplayer Python Racer", page_icon="🏎️", layout="centered")

st.title("🏎️ P2P Multiplayer Python Racer")
st.write("Play online with a friend over a direct Peer-to-Peer (P2P) connection!")

html_p2p_game = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>P2P Python Racer</title>
    <!-- PyScript CDN -->
    <link rel="stylesheet" href="https://pyscript.net/releases/2023.05.1/pyscript.css" />
    <script defer src="https://pyscript.net/releases/2023.05.1/pyscript.js"></script>
    <!-- PeerJS for P2P Networking -->
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
            padding: 15px 25px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            text-align: center;
            width: 460px;
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
            padding: 8px 15px;
            background-color: #e94560;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .lobby-panel button:hover { background-color: #0f3460; }
        #status-msg { margin-top: 10px; font-weight: bold; color: #f9d56e; }
        
        #gameCanvas {
            border: 4px solid #0f3460;
            background-color: #333;
            border-radius: 8px;
        }
        .controls-info {
            margin-top: 10px;
            font-size: 0.85em;
            color: #a2a8d3;
            text-align: center;
            max-width: 500px;
        }
        .p1-color { color: #00fff5; font-weight: bold; }
        .p2-color { color: #ff00ff; font-weight: bold; }
    </style>
</head>
<body>

    <!-- Lobby Section -->
    <div class="lobby-panel">
        <div>
            <strong>My Room ID:</strong> <span id="my-peer-id">Generating...</span>
        </div>
        <div style="margin-top: 10px;">
            <input type="text" id="join-id-input" placeholder="ROOM CODE" />
            <button onclick="connectToPeer()">Join Room</button>
        </div>
        <div id="status-msg">Waiting for connection...</div>
    </div>

    <!-- Canvas -->
    <canvas id="gameCanvas" width="500" height="480"></canvas>
    
    <div class="controls-info">
        👈 / 👉 <strong>Left / Right Arrows</strong> or <strong>A / D</strong> to steer | ⚡ <strong>Up Arrow / W</strong> for Nitro Boost<br>
        🪙 Collect Coins | 🔄 <strong>Spacebar</strong> to Restart
    </div>

    <!-- P2P JavaScript Layer -->
    <script>
        let peer = null;
        let conn = null;
        let isHost = false;
        let p2pDataHandler = null;

        // Initialize PeerJS
        function initPeer() {
            // Generate a short 5-character ID
            const shortId = Math.random().toString(36).substring(2, 7).toUpperCase();
            peer = new Peer(shortId);

            peer.on('open', (id) => {
                document.getElementById('my-peer-id').innerText = id;
            });

            // Handle incoming connections (When acting as Host)
            peer.on('connection', (connection) => {
                conn = connection;
                isHost = true;
                setupConnection();
            });
        }

        // Join another player's room
        function connectToPeer() {
            const joinId = document.getElementById('join-id-input').value.trim().toUpperCase();
            if (!joinId) return;
            
            document.getElementById('status-msg').innerText = "Connecting to " + joinId + "...";
            conn = peer.connect(joinId);
            isHost = false;
            setupConnection();
        }

        function setupConnection() {
            conn.on('open', () => {
                document.getElementById('status-msg').innerText = "🟢 Connected! " + (isHost ? "You are HOST (P1)" : "You are CLIENT (P2)");
            });

            conn.on('data', (data) => {
                if (p2pDataHandler) {
                    p2pDataHandler(data);
                }
            });

            conn.on('close', () => {
                document.getElementById('status-msg').innerText = "🔴 Connection Lost.";
            });
        }

        function sendP2PData(data) {
            if (conn && conn.open) {
                conn.send(data);
            }
        }

        window.onload = initPeer;
    </script>

    <!-- Game Engine -->
    <py-script>
import random
import math
import json
from js import document, window, sendP2PData
from pyodide.ffi import create_proxy

canvas = document.getElementById("gameCanvas")
ctx = canvas.getContext("2d")

lanes = [70, 180, 310, 420]
car_width = 34
car_height = 58

# Local and Remote Player States
my_player_num = 1  # 1 for Host, 2 for Client
p1 = {"lane": 1, "y": 400, "color": "#00fff5", "score": 0, "alive": True, "boosting": False}
p2 = {"lane": 2, "y": 400, "color": "#ff00ff", "score": 0, "alive": True, "boosting": False}

enemies = []
coins = []
enemy_colors = ["#ff0055", "#ffbe00", "#00ff66"]

level = 1
frame_count = 0
game_over = False

def handle_remote_data(data_json):
    global enemies, coins, game_over, level
    data = json.loads(data_json)
    
    # Received state sync from opponent
    if data["type"] == "player_input":
        remote_p = p2 if data["player"] == 2 else p1
        remote_p["lane"] = data["lane"]
        remote_p["boosting"] = data["boosting"]
        
    elif data["type"] == "host_sync":
        # Host syncs authoritative world state to client
        global enemies, coins, game_over
        enemies = data["enemies"]
        coins = data["coins"]
        game_over = data["game_over"]
        p1["score"] = data["p1_score"]
        p2["score"] = data["p2_score"]
        p1["alive"] = data["p1_alive"]
        p2["alive"] = data["p2_alive"]

# Register Python function to JavaScript
window.p2pDataHandler = create_proxy(handle_remote_data)

def draw_car(x, y, body_color, is_player=False, boosting=False):
    left_x = x - car_width // 2
    
    # Wheels
    ctx.fillStyle = "#111111"
    ctx.fillRect(left_x - 3, y + 8, 4, 12)
    ctx.fillRect(left_x + car_width - 1, y + 8, 4, 12)
    ctx.fillRect(left_x - 3, y + 40, 4, 12)
    ctx.fillRect(left_x + car_width - 1, y + 40, 4, 12)

    # Nitro Flame
    if is_player and boosting:
        ctx.fillStyle = "#ff5500"
        ctx.beginPath()
        ctx.moveTo(left_x + 8, y + car_height)
        ctx.lineTo(left_x + car_width // 2, y + car_height + random.randint(15, 25))
        ctx.lineTo(left_x + car_width - 8, y + car_height)
        ctx.fill()

    # Main Body
    ctx.fillStyle = body_color
    ctx.fillRect(left_x, y, car_width, car_height)

    # Windshield & Roof
    ctx.fillStyle = "#1a1a1a"
    ctx.fillRect(left_x + 4, y + 14, car_width - 8, 20)
    ctx.fillStyle = body_color
    ctx.fillRect(left_x + 6, y + 18, car_width - 12, 10)

    # Lights
    if is_player:
        ctx.fillStyle = "#ffff00"
        ctx.fillRect(left_x + 2, y + 2, 5, 4)
        ctx.fillRect(left_x + car_width - 7, y + 2, 5, 4)
    else:
        ctx.fillStyle = "#ffff00"
        ctx.fillRect(left_x + 2, y + car_height - 5, 5, 4)
        ctx.fillRect(left_x + car_width - 7, y + car_height - 5, 5, 4)

def draw_coin(x, y):
    ctx.fillStyle = "#ffd700"
    ctx.beginPath()
    ctx.arc(x, y, 11, 0, math.pi * 2)
    ctx.fill()
    ctx.strokeStyle = "#b8860b"
    ctx.lineWidth = 2
    ctx.stroke()

def send_my_state():
    is_host = window.isHost
    my_p_num = 1 if is_host else 2
    my_p = p1 if is_host else p2
    
    msg = json.dumps({
        "type": "player_input",
        "player": my_p_num,
        "lane": my_p["lane"],
        "boosting": my_p["boosting"]
    })
    sendP2PData(msg)

def on_key_down(event):
    is_host = window.isHost
    my_p = p1 if is_host else p2

    if my_p["alive"] and not game_over:
        if event.key in ["ArrowLeft", "a", "A"] and my_p["lane"] > 0:
            my_p["lane"] -= 1
            send_my_state()
        elif event.key in ["ArrowRight", "d", "D"] and my_p["lane"] < len(lanes) - 1:
            my_p["lane"] += 1
            send_my_state()
        elif event.key in ["ArrowUp", "w", "W"]:
            my_p["boosting"] = True
            send_my_state()

def on_key_up(event):
    is_host = window.isHost
    my_p = p1 if is_host else p2
    if event.key in ["ArrowUp", "w", "W"]:
        my_p["boosting"] = False
        send_my_state()

document.addEventListener("keydown", create_proxy(on_key_down))
document.addEventListener("keyup", create_proxy(on_key_up))

def game_loop(timestamp=None):
    global level, frame_count, game_over, enemies, coins

    is_host = window.isHost

    # 1. Host runs physics & collision logic
    if is_host and not game_over:
        max_score = max(p1["score"], p2["score"])
        level = (max_score // 100) + 1
        base_speed = 6 + (level * 1.2)
        
        any_boost = (p1["alive"] and p1["boosting"]) or (p2["alive"] and p2["boosting"])
        effective_speed = base_speed * (1.7 if any_boost else 1.0)

        # Spawning
        frame_count += 1
        if frame_count % max(16, int(40 - level * 2)) == 0:
            x = random.choice(lanes)
            color = random.choice(enemy_colors)
            enemies.append({"x": x, "y": -60, "color": color})

        if frame_count % 90 == 0:
            coins.append({"x": random.choice(lanes), "y": -30})

        # Move Coins
        for coin in coins[:]:
            coin["y"] += effective_speed
            for p in [p1, p2]:
                if p["alive"] and abs(lanes[p["lane"]] - coin["x"]) < 25 and abs(p["y"] - coin["y"]) < 30:
                    if coin in coins: coins.remove(coin)
                    p["score"] += 25
            if coin["y"] > 520 and coin in coins:
                coins.remove(coin)

        # Move Enemies & Check Collisions
        for enemy in enemies[:]:
            enemy["y"] += effective_speed
            for p in [p1, p2]:
                if p["alive"] and abs(lanes[p["lane"]] - enemy["x"]) < 28 and abs(p["y"] - enemy["y"]) < 45:
                    p["alive"] = False

            if enemy["y"] > 500:
                enemies.remove(enemy)
                for p in [p1, p2]:
                    if p["alive"]:
                        p["score"] += 20 if p["boosting"] else 10

        if not p1["alive"] and not p2["alive"]:
            game_over = True

        # Broadcast world state from Host to Client
        sync_msg = json.dumps({
            "type": "host_sync",
            "enemies": enemies,
            "coins": coins,
            "game_over": game_over,
            "p1_score": p1["score"],
            "p2_score": p2["score"],
            "p1_alive": p1["alive"],
            "p2_alive": p2["alive"]
        })
        sendP2PData(sync_msg)

    # 2. Rendering Phase (Both Host and Client)
    ctx.fillStyle = "#2d2d2d"
    ctx.fillRect(0, 0, 500, 480)

    # Road Dividers
    ctx.strokeStyle = "#ffffff"
    ctx.setLineDash([20, 15])
    ctx.beginPath()
    for divider_x in [125, 250, 375]:
        ctx.moveTo(divider_x, 0)
        ctx.lineTo(divider_x, 480)
    ctx.stroke()
    ctx.setLineDash([])

    # Draw Coins & Enemies
    for coin in coins:
        draw_coin(coin["x"], coin["y"])
    for enemy in enemies:
        draw_car(enemy["x"], enemy["y"], enemy["color"], is_player=False)

    # Draw Players
    if p1["alive"]:
        draw_car(lanes[p1["lane"]], p1["y"], p1["color"], is_player=True, boosting=p1["boosting"])
    if p2["alive"]:
        draw_car(lanes[p2["lane"]], p2["y"], p2["color"], is_player=True, boosting=p2["boosting"])

    # HUD
    ctx.font = "bold 13px Arial"
    ctx.fillStyle = p1["color"]
    ctx.fillText(f"P1 (Host): {p1['score']} pts", 15, 25)
    
    ctx.fillStyle = p2["color"]
    ctx.fillText(f"P2 (Client): {p2['score']} pts", 350, 25)

    if game_over:
        ctx.fillStyle = "rgba(0, 0, 0, 0.75)"
        ctx.fillRect(0, 0, 500, 480)
        ctx.fillStyle = "#ff0055"
        ctx.font = "bold 32px Arial"
        ctx.fillText("BOTH PLAYERS CRASHED", 65, 220)

    window.requestAnimationFrame(create_proxy(game_loop))

game_loop()
    </py-script>
</body>
</html>
"""

components.html(html_p2p_game, height=680, scrolling=False)