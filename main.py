import asyncio
import json
import random
import difflib
from aiohttp import web
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent

# ==========================================
# KONFIGURASI UTAMA
# ==========================================
TIKTOK_USERNAME = "c_poek"
PORT = 8080

# Dataset Gambar (Tambahkan URL gambar tak terbatas di sini)
# Format: {"url": "link_gambar", "answer": "jawaban"}
IMAGE_DB = [
    {"url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=800", "answer": "kucing"},
    {"url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=800", "answer": "anjing"},
    {"url": "https://images.unsplash.com/photo-1550258288-3fc06e67301c?w=800", "answer": "sepeda"},
    {"url": "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800", "answer": "mobil"},
    {"url": "https://images.unsplash.com/photo-1587590227264-0ac64ce63ce8?w=800", "answer": "gitar"},
]

# ==========================================
# GAME STATE & LOGIC
# ==========================================
class GameState:
    def __init__(self):
        self.current_image = ""
        self.current_answer = ""
        self.blur_level = 50
        self.zoom_level = 2.0
        self.winner = None
        self.time_left = 30
        self.clients = set()

state = GameState()

def check_answer(guess, correct):
    # Cek jawaban dengan toleransi typo (80% kemiripan)
    ratio = difflib.SequenceMatcher(None, guess.lower().strip(), correct.lower().strip()).ratio()
    return ratio >= 0.8

async def broadcast_state():
    if not state.clients:
        return
    
    payload = json.dumps({
        "image": state.current_image,
        "blur": state.blur_level,
        "zoom": state.zoom_level,
        "time": state.time_left,
        "winner": state.winner,
        "answer": state.current_answer if (state.winner or state.time_left <= 0) else "?"
    })
    
    for ws in list(state.clients):
        try:
            await ws.send_str(payload)
        except:
            state.clients.remove(ws)

async def game_loop():
    """Infinite loop untuk rotasi game."""
    while True:
        # 1. Setup Ronde Baru
        item = random.choice(IMAGE_DB)
        state.current_image = item["url"]
        state.current_answer = item["answer"]
        state.winner = None
        state.blur_level = 30 # Awal sangat blur
        state.zoom_level = 2.0 # Awal ter-zoom
        state.time_left = 30
        
        await broadcast_state()

        # 2. Countdown & Reveal Gambar Bertahap
        while state.time_left > 0 and not state.winner:
            await asyncio.sleep(1)
            state.time_left -= 1
            
            # Perlahan kurangi blur dan zoom agar gambar makin jelas
            if state.blur_level > 0:
                state.blur_level -= 1
            if state.zoom_level > 1.0:
                state.zoom_level -= 0.03
                
            await broadcast_state()

        # 3. Ronde Berakhir (Ada pemenang atau Waktu Habis)
        state.blur_level = 0
        state.zoom_level = 1.0
        await broadcast_state()
        
        # Jeda sebelum lanjut ronde berikutnya
        await asyncio.sleep(5)

# ==========================================
# TIKTOK LIVE INTEGRATION
# ==========================================
async def start_tiktok():
    """Koneksi ke TikTok Live (Tetap jalan meski offline)."""
    client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        # Jika belum ada pemenang dan ada yang komentar
        if not state.winner and state.time_left > 0:
            if check_answer(event.comment, state.current_answer):
                state.winner = event.user.nickname
                print(f"[WINNER] {state.winner} menebak benar: {event.comment}")
                await broadcast_state()

    while True:
        try:
            print(f"Menghubungkan ke TikTok LIVE @{TIKTOK_USERNAME}...")
            await client.start()
        except Exception as e:
            print(f"[STANDBY MODE] TikTok Live offline/error. Retrying in 30s...")
            await asyncio.sleep(30)

# ==========================================
# WEB SERVER & UI (HTML/CANVAS)
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tebak Gambar TikTok Live</title>
    <style>
        body {
            margin: 0; padding: 0; background-color: #0f0f0f; color: white;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex; justify-content: center; align-items: center;
            height: 100vh; overflow: hidden;
        }
        .game-container {
            width: 100vw; max-width: 133vh; aspect-ratio: 4/3;
            background: #1a1a1a; position: relative; overflow: hidden;
            box-shadow: 0 0 20px rgba(0,0,0,0.8);
        }
        #main-image {
            width: 100%; height: 100%; object-fit: cover;
            transition: filter 1s linear, transform 1s linear;
        }
        .overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; display: flex; flex-direction: column;
            justify-content: space-between; padding: 20px; box-sizing: border-box;
        }
        .header { display: flex; justify-content: space-between; align-items: flex-start; }
        .status-box {
            background: rgba(255, 0, 80, 0.9); padding: 10px 25px;
            border-radius: 30px; font-weight: bold; font-size: 24px;
            text-transform: uppercase; letter-spacing: 2px;
            box-shadow: 0 4px 15px rgba(255,0,80,0.4);
        }
        .timer {
            background: rgba(0, 0, 0, 0.8); padding: 10px 20px;
            border-radius: 15px; font-size: 30px; font-weight: bold;
            border: 2px solid #00f2fe; color: #00f2fe;
        }
        .winner-banner {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(0, 242, 254, 0.95); color: #000; padding: 30px 50px;
            border-radius: 20px; text-align: center; display: none;
            box-shadow: 0 0 50px rgba(0,242,254,0.6); animation: pop 0.5s ease-out forwards;
        }
        @keyframes pop {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        .winner-banner h2 { margin: 0; font-size: 40px; text-transform: uppercase; }
        .winner-banner p { margin: 10px 0 0; font-size: 24px; font-weight: bold; }
        .answer-reveal {
            position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.8); padding: 15px 40px; border-radius: 30px;
            font-size: 32px; font-weight: bold; letter-spacing: 3px;
            border: 2px solid #fff; text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <img id="main-image" src="" alt="Misteri">
        <div class="overlay">
            <div class="header">
                <div class="status-box" id="status-text">TEBAK GAMBAR!</div>
                <div class="timer" id="timer">30</div>
            </div>
            <div class="answer-reveal" id="answer-text">?????</div>
        </div>
        <div class="winner-banner" id="winner-banner">
            <h2>BENAR!</h2>
            <p id="winner-name">@username</p>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws`);
        const img = document.getElementById('main-image');
        const timerEl = document.getElementById('timer');
        const statusEl = document.getElementById('status-text');
        const winnerBanner = document.getElementById('winner-banner');
        const winnerName = document.getElementById('winner-name');
        const answerText = document.getElementById('answer-text');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update Gambar & Efek Modifikasi
            if(img.src !== data.image) img.src = data.image;
            img.style.filter = `blur(${data.blur}px) contrast(1.2)`;
            img.style.transform = `scale(${data.zoom})`;
            
            // Update Timer
            timerEl.innerText = data.time;
            
            // Update Jawaban
            answerText.innerText = data.answer;

            // Handle UI Pemenang / Waktu Habis
            if (data.winner) {
                statusEl.innerText = "ADA PEMENANG!";
                statusEl.style.background = "#00f2fe";
                statusEl.style.color = "#000";
                winnerName.innerText = "@" + data.winner;
                winnerBanner.style.display = "block";
                document.body.style.animation = "flash 0.5s";
            } else if (data.time <= 0) {
                statusEl.innerText = "WAKTU HABIS!";
                statusEl.style.background = "#ff0050";
                statusEl.style.color = "#fff";
                winnerBanner.style.display = "none";
            } else {
                statusEl.innerText = "TEBAK SEKARANG!";
                statusEl.style.background = "rgba(255, 0, 80, 0.9)";
                statusEl.style.color = "#fff";
                winnerBanner.style.display = "none";
                document.body.style.animation = "none";
            }
        };
    </script>
</body>
</html>
"""

async def index_handler(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    state.clients.add(ws)
    await broadcast_state() # Kirim state saat ini saat client baru connect
    
    try:
        async for msg in ws:
            pass # Hanya listen, tidak perlu proses pesan masuk dari browser
    finally:
        state.clients.remove(ws)
    return ws

# ==========================================
# MAIN EXECUTION
# ==========================================
async def main():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print(f"Server berjalan di http://localhost:{PORT}")
    
    # Jalankan Game Loop dan TikTok Client secara paralel di background
    await asyncio.gather(
        game_loop(),
        start_tiktok()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server dimatikan.")
