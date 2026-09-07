"""
Doodle Duel — a real-time, two-player drawing & guessing game built with Streamlit.

HOW THE "P2P" WORKS
--------------------
Browsers can't talk directly to each other in pure Streamlit (no WebRTC support
out of the box), so this app uses the lightest possible relay instead of a real
game server: a small SQLite file that both players' browser sessions read from
and write to. Each player opens the SAME app URL, types the SAME room code, and
the app polls the shared DB every couple of seconds so both screens stay in
sync. From the players' point of view it behaves like a direct peer session —
one device draws, the other watches and guesses live — there's just a tiny
file acting as the handshake in between instead of a dedicated backend.

To actually play across two separate devices (not just two browser tabs on one
computer) you need the app reachable from both devices — see the "How to play
on two devices" box in the sidebar once the app is running.

Run with:
    streamlit run app.py
"""

import base64
import io
import json
import random
import sqlite3
import string
import threading
import time
from datetime import datetime

import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from streamlit_drawable_canvas import st_canvas

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

DB_PATH = "doodle_duel.db"
_DB_LOCK = threading.Lock()

WORD_BANK = [
    "cat", "dog", "elephant", "guitar", "pizza", "rocket", "sunflower",
    "umbrella", "castle", "dinosaur", "bicycle", "octopus", "rainbow",
    "sandwich", "spider", "volcano", "airplane", "penguin", "robot",
    "mountain", "butterfly", "lighthouse", "snowman", "kangaroo",
    "sailboat", "cactus", "campfire", "dragon", "helicopter", "jellyfish",
    "ladder", "mushroom", "pretzel", "scarecrow", "telescope", "waterfall",
    "wizard", "koala", "pineapple", "unicorn",
]

st.set_page_config(page_title="Doodle Duel", page_icon="✏️", layout="centered")


# --------------------------------------------------------------------------- #
# Mobile-responsive styling
# --------------------------------------------------------------------------- #

def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 760px;
        }
        .stButton > button {
            width: 100%;
            padding: 0.6rem 1rem;
            font-size: 1rem;
            border-radius: 10px;
        }
        div[data-testid="stTextInput"] input {
            font-size: 1rem;
        }
        .guess-row {
            padding: 0.35rem 0.6rem;
            border-radius: 8px;
            margin-bottom: 0.3rem;
            font-size: 0.95rem;
        }
        .guess-correct { background: #d4f7dc; }
        .guess-wrong { background: #f2f2f2; }
        .room-code {
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: 3px;
            text-align: center;
            padding: 0.5rem;
            border: 2px dashed #999;
            border-radius: 10px;
            margin-bottom: 0.5rem;
        }
        /* Shrink everything a bit further on narrow / mobile screens */
        @media (max-width: 640px) {
            .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
            h1 { font-size: 1.4rem !important; }
            h2 { font-size: 1.15rem !important; }
            h3 { font-size: 1.0rem !important; }
            .room-code { font-size: 1.3rem; }
            .stButton > button { font-size: 0.95rem; padding: 0.55rem 0.8rem; }
        }
        canvas { max-width: 100% !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Database helpers (the "relay" between the two players)
# --------------------------------------------------------------------------- #

@st.cache_resource
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room_id      TEXT PRIMARY KEY,
            word         TEXT,
            artist_name  TEXT,
            guesser_name TEXT,
            drawing      TEXT,
            guesses      TEXT DEFAULT '[]',
            round_num    INTEGER DEFAULT 1,
            status       TEXT DEFAULT 'waiting',
            created_at   TEXT
        )
        """
    )
    conn.commit()
    return conn


def room_exists(room_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM rooms WHERE room_id = ?", (room_id,)).fetchone()
    return row is not None


def create_room(room_id: str, artist_name: str) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            """
            INSERT OR REPLACE INTO rooms
                (room_id, word, artist_name, guesser_name, drawing, guesses,
                 round_num, status, created_at)
            VALUES (?, NULL, ?, NULL, NULL, '[]', 1, 'waiting', ?)
            """,
            (room_id, artist_name, datetime.utcnow().isoformat()),
        )
        conn.commit()


def join_room_as_guesser(room_id: str, guesser_name: str) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            "UPDATE rooms SET guesser_name = ? WHERE room_id = ?",
            (guesser_name, room_id),
        )
        conn.commit()


def load_room(room_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT room_id, word, artist_name, guesser_name, drawing, guesses,
                  round_num, status, created_at
           FROM rooms WHERE room_id = ?""",
        (room_id,),
    ).fetchone()
    if row is None:
        return None
    keys = ["room_id", "word", "artist_name", "guesser_name", "drawing",
            "guesses", "round_num", "status", "created_at"]
    data = dict(zip(keys, row))
    data["guesses"] = json.loads(data["guesses"] or "[]")
    return data


def start_round(room_id: str, word: str) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            """UPDATE rooms
               SET word = ?, drawing = NULL, guesses = '[]', status = 'active'
               WHERE room_id = ?""",
            (word, room_id),
        )
        conn.commit()


def save_drawing(room_id: str, data_url: str) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            "UPDATE rooms SET drawing = ? WHERE room_id = ?",
            (data_url, room_id),
        )
        conn.commit()


def submit_guess(room_id: str, player: str, text: str, correct: bool) -> None:
    conn = get_connection()
    with _DB_LOCK:
        row = conn.execute(
            "SELECT guesses FROM rooms WHERE room_id = ?", (room_id,)
        ).fetchone()
        guesses = json.loads(row[0] or "[]")
        guesses.append({
            "player": player,
            "text": text,
            "correct": correct,
            "time": datetime.utcnow().strftime("%H:%M:%S"),
        })
        new_status = "won" if correct else "active"
        conn.execute(
            "UPDATE rooms SET guesses = ?, status = ? WHERE room_id = ?",
            (json.dumps(guesses), new_status, room_id),
        )
        conn.commit()


def next_round(room_id: str, round_num: int) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            """UPDATE rooms
               SET word = NULL, drawing = NULL, guesses = '[]',
                   round_num = ?, status = 'waiting'
               WHERE room_id = ?""",
            (round_num, room_id),
        )
        conn.commit()


def random_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


# --------------------------------------------------------------------------- #
# Canvas <-> base64 helpers
# --------------------------------------------------------------------------- #

def canvas_array_to_data_url(image_array) -> str | None:
    if image_array is None:
        return None
    img = Image.fromarray(image_array.astype("uint8"), "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def data_url_to_image(data_url: str) -> Image.Image:
    header, encoded = data_url.split(",", 1)
    return Image.open(io.BytesIO(base64.b64decode(encoded)))


# --------------------------------------------------------------------------- #
# UI: entry / lobby screen
# --------------------------------------------------------------------------- #

def lobby_screen() -> None:
    st.title("✏️ Doodle Duel")
    st.caption("One player draws, the other guesses — live, in real time.")

    with st.sidebar:
        st.subheader("How to play on two devices")
        st.markdown(
            "1. Deploy this app (e.g. Streamlit Community Cloud) or run it on "
            "a machine reachable from both devices, such as with a tunnel "
            "(ngrok, Cloudflare Tunnel).\n"
            "2. Open the app URL on **both** devices.\n"
            "3. One player creates a room and shares the 5-character code.\n"
            "4. The other player joins with that code.\n"
            "5. The artist draws, the guesser types guesses — both screens "
            "update automatically every couple of seconds."
        )

    tab_create, tab_join = st.tabs(["🎨 Create a room (Artist)", "🔍 Join a room (Guesser)"])

    with tab_create:
        name = st.text_input("Your name", key="create_name", placeholder="e.g. Salem")
        code = st.text_input(
            "Room code (leave blank to auto-generate)",
            key="create_code",
            placeholder="e.g. ABC12",
        ).strip().upper()
        if st.button("Create room", key="btn_create"):
            if not name.strip():
                st.error("Please enter your name.")
            else:
                room_id = code or random_room_code()
                if room_exists(room_id):
                    st.error("That room code is already taken — try another.")
                else:
                    create_room(room_id, name.strip())
                    st.session_state.room_id = room_id
                    st.session_state.role = "artist"
                    st.session_state.player_name = name.strip()
                    st.rerun()

    with tab_join:
        name2 = st.text_input("Your name", key="join_name", placeholder="e.g. Fatima")
        code2 = st.text_input("Room code", key="join_code", placeholder="e.g. ABC12").strip().upper()
        if st.button("Join room", key="btn_join"):
            if not name2.strip() or not code2:
                st.error("Please enter your name and the room code.")
            elif not room_exists(code2):
                st.error("No room found with that code. Ask the artist to double-check it.")
            else:
                join_room_as_guesser(code2, name2.strip())
                st.session_state.room_id = code2
                st.session_state.role = "guesser"
                st.session_state.player_name = name2.strip()
                st.rerun()


# --------------------------------------------------------------------------- #
# UI: artist screen
# --------------------------------------------------------------------------- #

def artist_screen(room: dict) -> None:
    st.markdown(f"<div class='room-code'>{room['room_id']}</div>", unsafe_allow_html=True)
    st.caption("Share this code with the other player so they can join.")

    if room["status"] == "waiting" or not room["word"]:
        st.subheader("Pick a word to draw")
        if "word_options" not in st.session_state or st.session_state.get("word_options_round") != room["round_num"]:
            st.session_state.word_options = random.sample(WORD_BANK, 3)
            st.session_state.word_options_round = room["round_num"]

        cols = st.columns(3)
        for i, w in enumerate(st.session_state.word_options):
            if cols[i].button(w.capitalize(), key=f"word_{w}_{room['round_num']}"):
                start_round(room["room_id"], w)
                st.rerun()

        custom = st.text_input("...or type your own word", key=f"custom_word_{room['round_num']}")
        if st.button("Use my word", key=f"btn_custom_word_{room['round_num']}"):
            if custom.strip():
                start_round(room["room_id"], custom.strip().lower())
                st.rerun()
            else:
                st.error("Type a word first.")
        return

    st.subheader(f"Your secret word: **{room['word']}**")
    if not room["guesser_name"]:
        st.info("Waiting for someone to join with the room code…")

    size = st.radio(
        "Canvas size", ["Mobile (small)", "Desktop (large)"],
        horizontal=True, key="canvas_size_choice",
    )
    canvas_w, canvas_h = (320, 260) if size.startswith("Mobile") else (640, 420)

    col1, col2 = st.columns([1, 1])
    stroke_width = col1.slider("Brush size", 2, 20, 5)
    stroke_color = col2.color_picker("Colour", "#111111")

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color="#FFFFFF",
        width=canvas_w,
        height=canvas_h,
        drawing_mode="freedraw",
        key=f"canvas_{room['room_id']}_{room['round_num']}",
        update_streamlit=True,
    )

    if canvas_result.image_data is not None:
        data_url = canvas_array_to_data_url(canvas_result.image_data)
        if data_url and data_url != st.session_state.get("last_saved_drawing"):
            save_drawing(room["room_id"], data_url)
            st.session_state.last_saved_drawing = data_url

    st.markdown("#### Guesses so far")
    render_guess_list(room["guesses"])

    if room["status"] == "won":
        winner = next((g["player"] for g in room["guesses"] if g["correct"]), room["guesser_name"])
        st.success(f"🎉 {winner} guessed it — the word was **{room['word']}**!")
        if st.button("Start a new round"):
            next_round(room["room_id"], room["round_num"] + 1)
            st.session_state.pop("last_saved_drawing", None)
            st.rerun()

    st_autorefresh(interval=2000, key=f"artist_refresh_{room['room_id']}")


# --------------------------------------------------------------------------- #
# UI: guesser screen
# --------------------------------------------------------------------------- #

def guesser_screen(room: dict) -> None:
    st.markdown(f"<div class='room-code'>{room['room_id']}</div>", unsafe_allow_html=True)

    if room["status"] == "waiting" or not room["word"]:
        st.info("Waiting for the artist to pick a word and start drawing…")
        st_autorefresh(interval=2000, key=f"guesser_refresh_wait_{room['room_id']}")
        return

    st.subheader("What is being drawn?")
    if room["drawing"]:
        img = data_url_to_image(room["drawing"])
        st.image(img, use_container_width=True)
    else:
        st.info("The artist hasn't started drawing yet — hang tight.")

    if room["status"] != "won":
        with st.form(key=f"guess_form_{room['room_id']}_{room['round_num']}", clear_on_submit=True):
            guess_text = st.text_input("Your guess")
            submitted = st.form_submit_button("Submit guess")
        if submitted and guess_text.strip():
            correct = guess_text.strip().lower() == (room["word"] or "").strip().lower()
            submit_guess(room["room_id"], st.session_state.player_name, guess_text.strip(), correct)
            st.rerun()
    else:
        st.success(f"🎉 The word was **{room['word']}**! Waiting for the artist to start a new round…")

    st.markdown("#### Guesses so far")
    render_guess_list(room["guesses"])

    st_autorefresh(interval=2000, key=f"guesser_refresh_{room['room_id']}")


# --------------------------------------------------------------------------- #
# Shared UI bits
# --------------------------------------------------------------------------- #

def render_guess_list(guesses: list) -> None:
    if not guesses:
        st.caption("No guesses yet.")
        return
    for g in reversed(guesses[-15:]):
        css_class = "guess-correct" if g["correct"] else "guess-wrong"
        icon = "✅" if g["correct"] else "❌"
        st.markdown(
            f"<div class='guess-row {css_class}'>{icon} <b>{g['player']}</b>: "
            f"{g['text']} <span style='color:#888;font-size:0.8rem;'>({g['time']})</span></div>",
            unsafe_allow_html=True,
        )


def leave_room_button() -> None:
    if st.button("⬅️ Leave room"):
        for k in ("room_id", "role", "player_name", "last_saved_drawing",
                  "word_options", "word_options_round"):
            st.session_state.pop(k, None)
        st.rerun()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    inject_css()
    get_connection()  # ensure DB/table exist

    if "room_id" not in st.session_state:
        lobby_screen()
        return

    room = load_room(st.session_state.room_id)
    if room is None:
        st.error("This room no longer exists.")
        leave_room_button()
        return

    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.write(f"Playing as **{st.session_state.player_name}** "
                 f"({'Artist' if st.session_state.role == 'artist' else 'Guesser'})")
    with top_right:
        leave_room_button()

    if st.session_state.role == "artist":
        artist_screen(room)
    else:
        guesser_screen(room)


if __name__ == "__main__":
    main()
