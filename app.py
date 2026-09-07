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

ROUNDS_PER_PLAYER = 5
TOTAL_ROUNDS = ROUNDS_PER_PLAYER * 2  # each of the two players draws 5 times
AUTO_ADVANCE_SECONDS = 4  # pause after a correct guess before the next round starts

WORD_BANK = [
    # Famous real people — historical & pop-culture icons
    "Albert Einstein", "Leonardo da Vinci", "William Shakespeare", "Cleopatra",
    "Isaac Newton", "Napoleon Bonaparte", "Mahatma Gandhi", "Nelson Mandela",
    "Marie Curie", "Muhammad Ali", "Michael Jackson", "Elvis Presley",
    "Charlie Chaplin", "Bruce Lee", "Pablo Picasso", "Walt Disney",
    "Steve Jobs", "Abraham Lincoln", "Bob Marley", "Cristiano Ronaldo",

    # Famous movie / TV characters
    "Spider-Man", "Batman", "Superman", "Iron Man", "Wonder Woman",
    "Darth Vader", "Yoda", "Luke Skywalker", "James Bond", "Indiana Jones",
    "Sherlock Holmes", "Harry Potter", "Dracula", "Frankenstein's Monster",
    "King Kong", "Godzilla", "The Joker", "Jack Sparrow", "Forrest Gump",

    # Widely known animated / cartoon characters
    "Mickey Mouse", "SpongeBob SquarePants", "Homer Simpson", "Shrek",
    "Winnie the Pooh", "Elsa", "Woody", "Buzz Lightyear", "Simba",
    "Pikachu", "Mario", "Sonic the Hedgehog", "Scooby-Doo", "Bugs Bunny",
]

st.set_page_config(page_title="Doodle Duel", page_icon="✏️", layout="centered")


# --------------------------------------------------------------------------- #
# Mobile-responsive styling
# --------------------------------------------------------------------------- #

def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Quicksand:wght@500;600;700&display=swap');

        :root {
            --ink: #201B2E;
            --paper: #FFF8EC;
            --coral: #FF6B6B;
            --sunny: #FFC93C;
            --sky: #3DB4F2;
            --grass: #3FC97C;
            --grape: #9B6BFF;
        }

        /* Sketchbook-paper backdrop: a faint dot grid, like graph paper */
        html, body, .stApp {
            background-color: var(--paper);
        }
        .stApp {
            background-image: radial-gradient(rgba(32,27,46,0.09) 1.4px, transparent 1.4px);
            background-size: 22px 22px;
        }

        html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
        h1, h2, h3, .room-code, .stButton > button, .score-chip {
            font-family: 'Baloo 2', sans-serif !important;
        }

        h1, h2, h3 {
            color: var(--ink);
        }
        h1 {
            text-decoration: underline wavy var(--sky);
            text-decoration-thickness: 3px;
            text-underline-offset: 8px;
        }

        /* Force our ink colour everywhere text appears, regardless of the
           visitor's light/dark system theme — Streamlit's own dark theme
           otherwise renders body text white, which disappears on our
           light paper background. */
        .stApp,
        .stApp p,
        .stApp span,
        .stApp label,
        .stApp li,
        .stApp div[data-testid="stMarkdownContainer"],
        .stApp div[data-testid="stMarkdownContainer"] *,
        .stApp label[data-testid="stWidgetLabel"],
        .stApp div[data-testid="stCaptionContainer"],
        .stApp div[data-testid="stMetricValue"],
        .stApp div[data-testid="stMetricLabel"],
        .stApp div[data-testid="stTextInput"] input,
        .stApp div[data-testid="stAlertContentSuccess"],
        .stApp div[data-testid="stAlertContentInfo"],
        .stApp div[data-testid="stAlertContentError"],
        .stApp div[data-testid="stAlertContentWarning"] {
            color: var(--ink) !important;
        }

        .block-container, .stMainBlockContainer {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 760px !important;
        }

        /* Chunky "sticker" buttons: thick ink border + hard offset shadow that
           grows on hover, instead of a soft SaaS drop-shadow.
           Streamlit wraps the real <button> in a div[data-testid="stButton"];
           target both that and the older .stButton class for safety, and
           force full width since Streamlit's own rules can win the width tie. */
        div[data-testid="stButton"] > button,
        .stButton > button {
            width: 100% !important;
            padding: 0.6rem 1rem;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--ink);
            background: #FFFFFF;
            border: 2.5px solid var(--ink);
            border-radius: 14px;
            box-shadow: 4px 4px 0 var(--ink);
            transition: transform 0.12s ease, box-shadow 0.12s ease;
        }
        div[data-testid="stButton"] > button:hover,
        .stButton > button:hover {
            background: var(--sky);
            color: var(--ink);
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0 var(--ink);
        }
        div[data-testid="stButton"] > button:active,
        .stButton > button:active {
            transform: translate(1px, 1px);
            box-shadow: 2px 2px 0 var(--ink);
        }

        div[data-testid="stTextInput"] input {
            font-size: 1rem;
            font-family: 'Quicksand', sans-serif;
            border: 2px solid var(--ink) !important;
            border-radius: 10px !important;
        }

        /* Guess feed: little alternating-tilt paper strips */
        .guess-row {
            padding: 0.4rem 0.7rem;
            border-radius: 10px;
            margin-bottom: 0.4rem;
            font-size: 0.95rem;
            background: #FFFFFF;
            border: 2px solid var(--ink);
            box-shadow: 3px 3px 0 rgba(32,27,46,0.25);
        }
        .guess-row:nth-child(odd) { transform: rotate(-0.6deg); }
        .guess-row:nth-child(even) { transform: rotate(0.6deg); }
        .guess-correct { border-color: var(--grass); background: #EAFBF1; }
        .guess-wrong { border-color: var(--coral); background: #FFF1F0; }

        /* Room code shown as a rotated name-badge sticker, with little
           washi-tape corners for a scrapbook feel */
        .room-code {
            position: relative;
            display: inline-block;
            font-size: 1.7rem;
            font-weight: 800;
            letter-spacing: 4px;
            text-align: center;
            padding: 0.55rem 1.4rem;
            background: var(--sunny);
            border: 3px solid var(--ink);
            border-radius: 14px;
            box-shadow: 5px 5px 0 var(--ink);
            transform: rotate(-2deg);
            margin: 0.3rem 0 1rem 0;
        }
        .room-code::before, .room-code::after {
            content: "";
            position: absolute;
            width: 34px; height: 14px;
            background: rgba(61, 180, 242, 0.55);
            border: 1px solid rgba(32,27,46,0.3);
            top: -10px;
        }
        .room-code::before { left: -6px; transform: rotate(-25deg); }
        .room-code::after { right: -6px; transform: rotate(25deg); }

        /* Score chips */
        .score-chip {
            display: inline-block;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 0.25rem 0.8rem;
            margin: 0 0.35rem 0.35rem 0;
            border-radius: 999px;
            border: 2px solid var(--ink);
            box-shadow: 2px 2px 0 var(--ink);
            color: var(--ink);
        }

        /* Role badge next to the player's name */
        .role-badge {
            display: inline-block;
            font-weight: 700;
            font-size: 0.9rem;
            padding: 0.15rem 0.7rem;
            border-radius: 999px;
            border: 2px solid var(--ink);
            margin-left: 0.4rem;
        }

        /* Playful alert banners instead of the flat default look */
        div[data-testid="stAlert"] {
            border: 2.5px solid var(--ink) !important;
            border-radius: 14px !important;
            box-shadow: 4px 4px 0 rgba(32,27,46,0.25);
            font-family: 'Quicksand', sans-serif;
        }

        /* Folder-tab style for the lobby's Create/Join tabs */
        button[data-baseweb="tab"] {
            font-family: 'Baloo 2', sans-serif;
            font-weight: 700;
            border-radius: 10px 10px 0 0 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: var(--sky) !important;
            height: 4px !important;
        }

        /* Metric cards on the game-over screen */
        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 2.5px solid var(--ink);
            border-radius: 14px;
            padding: 0.6rem 0.4rem;
            box-shadow: 4px 4px 0 var(--ink);
        }

        /* Shrink everything a bit further on narrow / mobile screens */
        @media (max-width: 640px) {
            .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.2rem !important; }
            h3 { font-size: 1.05rem !important; }
            .room-code { font-size: 1.25rem; padding: 0.45rem 1rem; letter-spacing: 3px; }
            .stButton > button { font-size: 1rem; padding: 0.6rem 0.8rem; }
        }
        canvas { max-width: 100% !important; }

        @media (prefers-reduced-motion: reduce) {
            * { transition: none !important; animation: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


PLAYER_COLORS = ["var(--sky)", "var(--grape)", "var(--sunny)", "var(--grass)", "var(--coral)"]


def render_scoreboard(scores: dict) -> None:
    if not scores:
        return
    chips = "".join(
        f'<span class="score-chip" style="background:{PLAYER_COLORS[i % len(PLAYER_COLORS)]}">'
        f'{name}: {points}</span>'
        for i, (name, points) in enumerate(scores.items())
    )
    st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)


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
            scores       TEXT DEFAULT '{}',
            round_num    INTEGER DEFAULT 1,
            status       TEXT DEFAULT 'waiting',
            won_at       TEXT,
            created_at   TEXT
        )
        """
    )
    # Migrate DB files created by older versions of this app.
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(rooms)").fetchall()}
    if "scores" not in existing_cols:
        conn.execute("ALTER TABLE rooms ADD COLUMN scores TEXT DEFAULT '{}'")
    if "won_at" not in existing_cols:
        conn.execute("ALTER TABLE rooms ADD COLUMN won_at TEXT")
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
                 scores, round_num, status, won_at, created_at)
            VALUES (?, NULL, ?, NULL, NULL, '[]', '{}', 1, 'waiting', NULL, ?)
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
                  scores, round_num, status, won_at, created_at
           FROM rooms WHERE room_id = ?""",
        (room_id,),
    ).fetchone()
    if row is None:
        return None
    keys = ["room_id", "word", "artist_name", "guesser_name", "drawing",
            "guesses", "scores", "round_num", "status", "won_at", "created_at"]
    data = dict(zip(keys, row))
    data["guesses"] = json.loads(data["guesses"] or "[]")
    data["scores"] = json.loads(data["scores"] or "{}")
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
            "SELECT guesses, scores FROM rooms WHERE room_id = ?", (room_id,)
        ).fetchone()
        guesses = json.loads(row[0] or "[]")
        scores = json.loads(row[1] or "{}")
        guesses.append({
            "player": player,
            "text": text,
            "correct": correct,
            "time": datetime.utcnow().strftime("%H:%M:%S"),
        })
        if correct:
            scores[player] = scores.get(player, 0) + 1
            conn.execute(
                """UPDATE rooms
                   SET guesses = ?, scores = ?, status = 'won', won_at = ?
                   WHERE room_id = ?""",
                (json.dumps(guesses), json.dumps(scores), datetime.utcnow().isoformat(), room_id),
            )
        else:
            conn.execute(
                "UPDATE rooms SET guesses = ?, status = 'active' WHERE room_id = ?",
                (json.dumps(guesses), room_id),
            )
        conn.commit()


def advance_or_finish(room_id: str, round_num: int) -> None:
    """Automatically move on from a won round: swap artist/guesser and start
    the next round, or end the game if that was the last one.

    Guarded with ``WHERE status = 'won'`` so that if both players' browsers
    happen to trigger this at the same moment, only the first one actually
    changes anything — the second becomes a harmless no-op.
    """
    conn = get_connection()
    next_num = round_num + 1
    with _DB_LOCK:
        if next_num > TOTAL_ROUNDS:
            conn.execute(
                "UPDATE rooms SET status = 'finished' WHERE room_id = ? AND status = 'won'",
                (room_id,),
            )
        else:
            conn.execute(
                """UPDATE rooms
                   SET artist_name = guesser_name,
                       guesser_name = artist_name,
                       word = NULL, drawing = NULL, guesses = '[]',
                       round_num = ?, status = 'waiting', won_at = NULL
                   WHERE room_id = ? AND status = 'won'""",
                (next_num, room_id),
            )
        conn.commit()


def reset_game(room_id: str) -> None:
    conn = get_connection()
    with _DB_LOCK:
        conn.execute(
            """UPDATE rooms
               SET word = NULL, drawing = NULL, guesses = '[]', scores = '{}',
                   round_num = 1, status = 'waiting', won_at = NULL
               WHERE room_id = ?""",
            (room_id,),
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
    st.caption(f"One player draws, the other guesses — {ROUNDS_PER_PLAYER} rounds each, roles swap automatically.")

    with st.sidebar:
        st.subheader("How to play on two devices")
        st.markdown(
            "1. Deploy this app (e.g. Streamlit Community Cloud) or run it on "
            "a machine reachable from both devices, such as with a tunnel "
            "(ngrok, Cloudflare Tunnel).\n"
            "2. Open the app URL on **both** devices.\n"
            "3. One player creates a room and shares the 5-character code.\n"
            "4. The other player joins with that code.\n"
            "5. The artist picks from 3 random word suggestions (famous "
            "people, movie characters, and cartoon icons) and draws; the "
            "guesser types guesses live.\n"
            f"6. After each correct guess, roles swap automatically. The "
            f"game runs {TOTAL_ROUNDS} rounds total ({ROUNDS_PER_PLAYER} as "
            "artist for each player), then shows the final score."
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
    st.caption(f"Round {room['round_num']} of {TOTAL_ROUNDS} · share this code so the other player can join.")

    if room["status"] == "waiting" or not room["word"]:
        st.subheader("Pick a word to draw")
        if "word_options" not in st.session_state or st.session_state.get("word_options_round") != room["round_num"]:
            st.session_state.word_options = random.sample(WORD_BANK, 3)
            st.session_state.word_options_round = room["round_num"]

        cols = st.columns(3)
        for i, w in enumerate(st.session_state.word_options):
            if cols[i].button(w, key=f"word_{w}_{room['round_num']}"):
                start_round(room["room_id"], w)
                st.rerun()

        if st.button("🔀 Shuffle suggestions", key=f"shuffle_{room['round_num']}"):
            st.session_state.word_options = random.sample(WORD_BANK, 3)
            st.rerun()
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
        return_image_data=True,
    )

    if canvas_result.image_data is not None:
        data_url = canvas_array_to_data_url(canvas_result.image_data)
        if data_url and data_url != st.session_state.get("last_saved_drawing"):
            save_drawing(room["room_id"], data_url)
            st.session_state.last_saved_drawing = data_url

    st.markdown("#### Guesses so far")
    render_guess_list(room["guesses"])

    if room["status"] == "won":
        render_won_banner(room)

    st_autorefresh(interval=2000, key=f"artist_refresh_{room['room_id']}")


# --------------------------------------------------------------------------- #
# UI: guesser screen
# --------------------------------------------------------------------------- #

def guesser_screen(room: dict) -> None:
    st.markdown(f"<div class='room-code'>{room['room_id']}</div>", unsafe_allow_html=True)
    st.caption(f"Round {room['round_num']} of {TOTAL_ROUNDS}")

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
            if correct:
                st.balloons()
            st.rerun()
    else:
        render_won_banner(room)

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


def render_won_banner(room: dict) -> None:
    """Shown to both players once the word is guessed. The next round starts
    on its own after a short pause — and roles swap automatically."""
    winner = next((g["player"] for g in room["guesses"] if g["correct"]), room["guesser_name"])
    next_artist = room["guesser_name"]  # whoever guessed correctly draws next
    st.success(f"🎉 {winner} guessed it — the word was **{room['word']}**!")

    elapsed = AUTO_ADVANCE_SECONDS
    if room.get("won_at"):
        elapsed = (datetime.utcnow() - datetime.fromisoformat(room["won_at"])).total_seconds()
    remaining = max(0, round(AUTO_ADVANCE_SECONDS - elapsed))

    is_last_round = room["round_num"] >= TOTAL_ROUNDS
    if is_last_round:
        st.caption(f"That was the last round — final scores in {remaining}s…")
    else:
        st.caption(f"Next up, **{next_artist}** draws and **{room['artist_name']}** guesses — starting in {remaining}s…")

    if elapsed >= AUTO_ADVANCE_SECONDS:
        advance_or_finish(room["room_id"], room["round_num"])
        st.session_state.pop("last_saved_drawing", None)
        st.rerun()


def render_game_over(room: dict) -> None:
    st.markdown(f"<div class='room-code'>{room['room_id']}</div>", unsafe_allow_html=True)
    st.title("🏁 Game over!")

    if st.session_state.get("celebrated_finish") != room["room_id"]:
        st.balloons()
        st.session_state["celebrated_finish"] = room["room_id"]

    players = sorted({room["artist_name"], room["guesser_name"]} - {None})
    scores = room["scores"]
    cols = st.columns(len(players)) if players else []
    for col, p in zip(cols, players):
        col.metric(p, scores.get(p, 0))

    if len(players) == 2:
        s0, s1 = scores.get(players[0], 0), scores.get(players[1], 0)
        if s0 > s1:
            st.success(f"🏆 **{players[0]}** wins!")
        elif s1 > s0:
            st.success(f"🏆 **{players[1]}** wins!")
        else:
            st.info("🤝 It's a tie!")

    if st.button("🔁 Play again (same room, same players)"):
        reset_game(room["room_id"])
        for k in ("last_saved_drawing", "word_options", "word_options_round", "celebrated_finish"):
            st.session_state.pop(k, None)
        st.rerun()

    st_autorefresh(interval=3000, key=f"gameover_refresh_{room['room_id']}")


def leave_room_button() -> None:
    if st.button("⬅️ Leave room"):
        for k in ("room_id", "role", "player_name", "last_saved_drawing",
                  "word_options", "word_options_round", "celebrated_finish"):
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

    if room["status"] == "finished":
        top_left, top_right = st.columns([3, 1])
        with top_right:
            leave_room_button()
        render_game_over(room)
        return

    # Roles can swap after each round, so figure out this client's CURRENT
    # role from the shared room state rather than trusting whatever role
    # they joined as.
    name = st.session_state.player_name
    if name == room["artist_name"]:
        current_role = "artist"
    elif room["guesser_name"] and name == room["guesser_name"]:
        current_role = "guesser"
    else:
        current_role = st.session_state.role  # fallback, shouldn't normally hit
    st.session_state.role = current_role

    top_left, top_right = st.columns([3, 1])
    with top_left:
        role_color = "var(--sky)" if current_role == "artist" else "var(--grape)"
        role_label = "Artist ✏️" if current_role == "artist" else "Guesser 🔍"
        st.markdown(
            f"Playing as **{name}** "
            f'<span class="role-badge" style="background:{role_color}">{role_label}</span>',
            unsafe_allow_html=True,
        )
        render_scoreboard(room["scores"])
    with top_right:
        leave_room_button()

    if current_role == "artist":
        artist_screen(room)
    else:
        guesser_screen(room)


if __name__ == "__main__":
    main()
