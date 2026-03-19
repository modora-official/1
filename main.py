import asyncio
import json
import random
import difflib
from aiohttp import web
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

# Konfigurasi TikTok LIVE
TIKTOK_USERNAME = "c_poek"

# Dataset Gambar & Jawaban (Kamu bisa tambah dataset ini sebanyak mungkin)
# Gunakan URL gambar direct (jpg/png)
DATASET = [
    {"url": "https://upload.wikimedia.org/wikipedia/commons/1/15/Red_Apple.jpg", "answer": "apel"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg", "answer": "kucing"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/2/25/2015_Mazda_MX-5_ND_2.0_SKYACTIV-G_160_i-ELOOP_Rubinrot-Metallic_Vorderansicht.jpg", "answer": "mobil"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/4/41/Left_side_of_Flying_Pigeon.jpg", "answer": "sepeda"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/d/d9/Collage_of_Nine_Dogs.jpg", "answer": "anjing"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/e/e4/Motorcycles_parked.jpg", "answer": "motor"}
]

# --- GAME STATE ---
game_state = {
    "active": False,
    "current_answer": "",
    "current_url": "",
    "blur": 30, # Start with heavy blur (px)
    "scale": 3.0, # Start with 3x zoom
    "timer": 60, # 60 seconds reveal
    "winner": None
}

websockets = set()

# --- HELPER FUNCTIONS ---
def check_answer(guess, correct):
    # Typo tolerance ringan (case insensitive, match ratio > 80%)
    guess = str(guess).lower().strip()
    correct = str(correct).lower().strip()
    ratio = difflib.SequenceMatcher(None, guess, correct).ratio()
    return ratio >= 0.8

async def broadcast(message_type, data):
    if not websockets: return
    msg = json.dumps({"type": message_type, "data": data})
    await asyncio.gather(*[ws.send_str(msg) for ws in websockets])

async def start_new_round():
    item = random.choice(DATASET)
    game_state["active"] = True
    game_state["current_answer"] = item["answer"]
    game_state["current_url"] = item["url"]
    game_state["blur"] = 40
    game_state["scale"] = 3.0
    game_state["timer"] = 60
    game_state["winner"] = None
    
    print(f"\n[+] RONDE BARU DIMULAI! Jawaban: {item['answer']}")
    await broadcast("new_round", game_state)

async def game_loop():
    # Infinite loop game engine
    await asyncio.sleep(2)
    await start_new_round()
    
    while True:
        await asyncio.sleep(1)
        if game_state["active"]:
            # Kurangi blur dan zoom secara bertahap seiring waktu
            if game_state["blur"] > 0:
                game_state["blur"] -= 0.6
            if game_state["scale"] > 1.0:
                game_state["scale"] -= 0.03
            
            game_state["timer"] -= 1
            
            await broadcast("update_effect", {"blur": max(0, game_state["blur"]), "scale": max(1, game_state["scale"])})

            # Jika waktu habis dan tidak ada yang tebak, reveal dan lanjut
            if game_state["timer"] <= 0:
                print("[-] Waktu habis, tidak ada yang menebak.")
                game_state["active"] = False
                await broadcast("reveal", {"answer": game_state["current_answer"]})
                await asyncio.sleep(4) # Tahan gambar jelas 4 detik
                await start_new_round()

# --- TIKTOK LIVE CLIENT ---
client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"[*] Terhubung ke TikTok LIVE: @{event.unique_id}")

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if not game_state["active"]: return
    
    guess = event.comment
    username = event.user.nickname
    
    if check_answer(guess, game_state["current_answer"]):
        print(f"[WIN] {username} menebak benar: {guess} (Jawaban: {game_state['current_answer']})")
        game_state["active"] = False # Stop ronde
        game_state["winner"] = username
        
        # Broadcast pemenang, hilangkan efek agar jelas
        await broadcast("winner", {
            "winner": username, 
            "guess": guess, 
            "answer": game_state["current_answer"]
        })
        
        await asyncio.sleep(5) # Tampilkan pemenang selama 5 detik
        await start_new_round() # Lanjut otomatis (Infinite loop)

# --- WEB SERVER & FRONTEND UI ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tebak Gambar LIVE</title>
    <style>
        body, html {
            margin: 0; padding: 0; background: #000; color: white;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex; justify-content: center; align-items: center;
            height: 100vh; overflow: hidden;
        }
        /* Aspek Rasio 4:3 Wajib */
        #game-container {
            aspect-ratio: 4/3;
            width: 100vw;
            max-width: calc(100vh * 4 / 3);
            max-height: 100vh;
            background: #111;
            position: relative;
            overflow: hidden;
            display: flex; justify-content: center; align-items: center;
        }
        #game-image {
            width: 100%; height: 100%;
            object-fit: cover;
            transition: filter 1s linear, transform 1s linear;
        }
        /* UI Overlays */
        #overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none;
            display: flex; flex-direction: column; justify-content: space-between;
        }
        .header {
            background: rgba(0,0,0,0.7); padding: 15px; text-align: center;
            font-size: 2vw; font-weight: bold; text-transform: uppercase;
            letter-spacing: 2px;
        }
        .footer {
            background: rgba(0,0,0,0.8); padding: 20px; text-align: center;
            font-size: 2.5vw; font-weight: bold; color: #ffeb3b;
        }
        #winner-banner {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(0, 255, 0, 0.9); color: black;
            padding: 30px; border-radius: 15px; text-align: center;
            font-size: 3vw; font-weight: bold; display: none;
            box-shadow: 0 0 30px rgba(0,255,0,0.8);
            animation: popIn 0.3s ease-out;
        }
        #flash-effect {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: white; opacity: 0; pointer-events: none;
            transition: opacity 0.2s;
        }
        @keyframes popIn {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        #fullscreen-btn {
            position: absolute; z-index: 1000; top: 10px; right: 10px;
            padding: 10px; background: red; color: white; border: none; cursor: pointer;
        }
    </style>
</head>
<body>
    <button id="fullscreen-btn" onclick="openFullscreen()">FULLSCREEN</button>
    <div id="game-container">
        <img id="game-image" src="" style="filter: blur(40px); transform: scale(3.0);">
        <div id="flash-effect"></div>
        <div id="overlay">
            <div class="header" id="status-text">🔥 TEBAK GAMBAR SEKARANG! 🔥</div>
            <div class="footer">JAWAB DI KOMENTAR!</div>
        </div>
        <div id="winner-banner">
            <div style="font-size: 1.5em;" id="winner-name">USERNAME</div>
            <div style="font-size: 0.8em; margin-top: 10px;">BENAR MENEBAK: <span id="correct-answer"></span></div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws`);
        const img = document.getElementById('game-image');
        const winnerBanner = document.getElementById('winner-banner');
        const winnerName = document.getElementById('winner-name');
        const correctAnswer = document.getElementById('correct-answer');
        const statusText = document.getElementById('status-text');
        const flashEffect = document.getElementById('flash-effect');

        function openFullscreen() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) { elem.requestFullscreen(); }
            document.getElementById('fullscreen-btn').style.display = 'none';
        }

        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            
            if (msg.type === "new_round") {
                img.src = msg.data.current_url;
                img.style.filter = `blur(${msg.data.blur}px)`;
                img.style.transform = `scale(${msg.data.scale})`;
                winnerBanner.style.display = "none";
                statusText.innerText = "🔥 TEBAK GAMBAR SEKARANG! 🔥";
                statusText.style.background = "rgba(0,0,0,0.7)";
            } 
            else if (msg.type === "update_effect") {
                img.style.filter = `blur(${msg.data.blur}px)`;
                img.style.transform = `scale(${msg.data.scale})`;
            }
            else if (msg.type === "winner") {
                // Efek Flash
                flashEffect.style.opacity = 1;
                setTimeout(() => { flashEffect.style.opacity = 0; }, 200);
                
                // Clear gambar penuh
                img.style.filter = "blur(0px)";
                img.style.transform = "scale(1)";
                
                // Tampilkan Pemenang
                winnerName.innerText = msg.data.winner;
                correctAnswer.innerText = msg.data.answer.toUpperCase();
                winnerBanner.style.display = "block";
                statusText.innerText = "🎉 ADA YANG BENAR! 🎉";
                statusText.style.background = "rgba(0,128,0,0.8)";
            }
            else if (msg.type === "reveal") {
                img.style.filter = "blur(0px)";
                img.style.transform = "scale(1)";
                statusText.innerText = `JAWABAN: ${msg.data.answer.toUpperCase()}`;
            }
        };
    </script>
</body>
</html>
"""

async def handle_index(request):
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    websockets.add(ws)
    try:
        async for msg in ws: pass
    finally:
        websockets.remove(ws)
    return ws

async def main():
    # Setup Web Server aiohttp
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/ws', handle_ws)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("[*] Local Server berjalan di: http://127.0.0.1:8080")
    print("[*] Buka URL tersebut di browser HP dan tap tombol FULLSCREEN.")

    # Jalankan Game Loop dan TikTok Live Client bersamaan
    await asyncio.gather(
        game_loop(),
        client.start()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[-] Server dimatikan.")