import asyncio
import random
from aiohttp import web
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

# ==========================================
# KONFIGURASI UTAMA
# ==========================================
TIKTOK_USERNAME = "c_poek"
PORT = 8080

# Database Soal (Jawaban ID : Prompt EN untuk digenerate gambarnya)
SOAL_DB = {
    "KUCING": "a cute cat standing", 
    "ANJING": "a cute dog", 
    "MOBIL": "a fast sports car",
    "SEPEDA": "a bicycle parked", 
    "PESAWAT": "an airplane flying in the sky", 
    "RUMAH": "a modern beautiful house",
    "POHON": "a big green tree", 
    "GUNUNG": "a beautiful mountain landscape", 
    "LAUTAN": "blue ocean waves",
    "BINTANG": "stars glowing in the night sky", 
    "KOMPUTER": "a desktop computer on a desk", 
    "SEPATU": "a pair of sneakers",
    "HELM": "a motorcycle helmet", 
    "KACAMATA": "sunglasses", 
    "JAM TANGAN": "an elegant wristwatch"
}

# ==========================================
# USER INTERFACE (HTML/CSS/JS)
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tebak Gambar TikTok LIVE</title>
    <style>
        body, html {
            margin: 0; padding: 0; width: 100%; height: 100%;
            background-color: #050505; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex; justify-content: center; align-items: center; overflow: hidden;
        }
        /* Memaksa rasio 4:3 untuk layar LIVE */
        #game-container {
            width: 100vw; height: 75vw; max-width: 133.33vh; max-height: 100vh;
            background: #111; position: relative; border: 2px solid #333;
            box-shadow: 0 0 30px rgba(0, 0, 0, 0.8); overflow: hidden;
        }
        #image-box {
            width: 100%; height: 100%; object-fit: cover;
            transition: filter 1s ease-in-out; filter: blur(40px);
        }
        .overlay {
            position: absolute; bottom: 0; width: 100%; background: linear-gradient(transparent, rgba(0,0,0,0.9));
            padding: 30px 20px 20px 20px; box-sizing: border-box; text-align: center;
        }
        #hint { font-size: 4rem; font-weight: 900; letter-spacing: 15px; margin: 0; color: #ffeb3b; text-shadow: 2px 2px 4px #000; }
        #timer { 
            font-size: 2.5rem; color: #ff5252; position: absolute; top: 20px; right: 20px;
            background: rgba(0,0,0,0.6); padding: 10px 25px; border-radius: 12px; font-weight: bold; border: 2px solid #ff5252;
        }
        #winner-alert {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(76, 175, 80, 0.95); padding: 40px; border-radius: 20px;
            text-align: center; display: none; z-index: 10; width: 80%; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 3px solid #fff;
        }
        #winner-alert h1 { margin: 0; font-size: 4rem; color: white; text-transform: uppercase; }
        #winner-alert p { font-size: 2.5rem; margin: 15px 0 0 0; color: #ffff00; font-weight: bold;}
        #status { position: absolute; top: 20px; left: 20px; font-size: 1.2rem; color: #aaa; background: rgba(0,0,0,0.6); padding: 8px 15px; border-radius: 8px;}
    </style>
</head>
<body>
    <div id="game-container">
        <div id="status">🔴 Menunggu Koneksi...</div>
        <div id="timer">30s</div>
        <img id="image-box" src="" alt="Mystery Image">
        <div class="overlay">
            <p id="hint">_ _ _ _ _</p>
        </div>
        <div id="winner-alert">
            <h1>JAWABAN BENAR! 🎉</h1>
            <p id="winner-name">@username</p>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://' + location.host + '/ws');
        const imgBox = document.getElementById('image-box');
        const hintText = document.getElementById('hint');
        const timerText = document.getElementById('timer');
        const winnerAlert = document.getElementById('winner-alert');
        const winnerName = document.getElementById('winner-name');
        const statusText = document.getElementById('status');

        ws.onopen = () => { statusText.innerHTML = '🟢 Game Berjalan (@c_poek)'; };
        ws.onclose = () => { statusText.innerHTML = '🔴 Terputus (Mencoba ulang...)'; setTimeout(() => location.reload(), 3000); };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_round') {
                winnerAlert.style.display = 'none';
                imgBox.src = data.image_url;
                imgBox.style.filter = `blur(${data.blur}px)`;
                hintText.innerHTML = data.hint;
            } 
            else if (data.type === 'tick') {
                timerText.innerHTML = data.time + 's';
                imgBox.style.filter = `blur(${data.blur}px)`; // Blur semakin hilang
                hintText.innerHTML = data.hint;
            }
            else if (data.type === 'winner') {
                imgBox.style.filter = 'blur(0px)'; // Gambar langsung jelas
                hintText.innerHTML = data.word;
                winnerName.innerHTML = '@' + data.username;
                winnerAlert.style.display = 'block';
            }
            else if (data.type === 'skip') {
                imgBox.style.filter = 'blur(0px)';
                hintText.innerHTML = "WAKTU HABIS! Jawabannya: " + data.word;
            }
        };
    </script>
</body>
</html>
"""

# ==========================================
# GAME LOGIC & SERVER
# ==========================================
class GameServer:
    def __init__(self):
        self.clients = set()
        self.current_word = ""
        self.current_image = ""
        self.timer = 45 # Waktu per ronde (detik)
        self.round_active = False
        self.revealed_indices = []

    def generate_hint(self):
        hint = ""
        for i, char in enumerate(self.current_word):
            if char == " ":
                hint += "  "
            elif i in self.revealed_indices:
                hint += char + " "
            else:
                hint += "_ "
        return hint.strip()

    async def broadcast(self, message):
        for ws in set(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                self.clients.discard(ws)

    async def start_new_round(self):
        self.current_word, prompt = random.choice(list(SOAL_DB.items()))
        # Bypass API key using free Pollinations API
        self.current_image = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=768&nologo=true&seed={random.randint(1,999999)}"
        self.timer = 45
        self.round_active = True
        self.revealed_indices = []
        
        # Buka 1 huruf acak sebagai petunjuk awal
        if len(self.current_word.replace(" ", "")) > 0:
            first_idx = random.choice([i for i, c in enumerate(self.current_word) if c != " "])
            self.revealed_indices.append(first_idx)

        await self.broadcast({
            "type": "new_round",
            "image_url": self.current_image,
            "hint": self.generate_hint(),
            "blur": 40
        })

    async def handle_winner(self, username):
        if not self.round_active: return
        self.round_active = False
        await self.broadcast({
            "type": "winner",
            "username": username,
            "word": self.current_word
        })
        await asyncio.sleep(4) # Tunggu 4 detik sebelum lanjut soal baru
        await self.start_new_round()

    async def game_loop(self):
        await self.start_new_round()
        while True:
            await asyncio.sleep(1)
            if self.round_active:
                self.timer -= 1
                
                # Blur menurun seiring berjalannya waktu (mulai dari 40px ke 0px)
                current_blur = max(0, int((self.timer / 45) * 40))

                # Tambah petunjuk huruf baru setiap 12 detik
                if self.timer % 12 == 0 and self.timer < 45 and self.timer > 0:
                    unrevealed = [i for i, c in enumerate(self.current_word) if i not in self.revealed_indices and c != " "]
                    if unrevealed:
                        self.revealed_indices.append(random.choice(unrevealed))

                await self.broadcast({
                    "type": "tick",
                    "time": self.timer,
                    "hint": self.generate_hint(),
                    "blur": current_blur
                })

                if self.timer <= 0:
                    self.round_active = False
                    await self.broadcast({
                        "type": "skip",
                        "word": self.current_word
                    })
                    await asyncio.sleep(4)
                    await self.start_new_round()

game = GameServer()

async def handle_index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def handle_websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    game.clients.add(ws)
    try:
        if game.round_active:
             await ws.send_json({
                "type": "new_round",
                "image_url": game.current_image,
                "hint": game.generate_hint(),
                "blur": max(0, int((game.timer / 45) * 40))
            })
        async for msg in ws: pass 
    finally:
        game.clients.discard(ws)
    return ws

# ==========================================
# TIKTOK LIVE CLIENT
# ==========================================
client = TikTokLiveClient(TIKTOK_USERNAME)

@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"✅ Terhubung ke TikTok LIVE: @{event.room_id}")

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if game.round_active:
        user_answer = event.comment.strip().upper()
        # Jika komentar sesuai dengan jawaban yang benar
        if game.current_word == user_answer:
            print(f"🎉 {event.user.unique_id} BENAR: {user_answer}")
            asyncio.create_task(game.handle_winner(event.user.unique_id))

async def main():
    app = web.Application()
    app.add_routes([web.get('/', handle_index), web.get('/ws', handle_websocket)])
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    
    print(f"🚀 Server UI berjalan di http://localhost:{PORT}")
    print("Silakan buka alamat di atas di browser Anda (ubah menjadi Fullscreen)")
    
    # Jalankan UI, Game Loop, dan Koneksi TikTok sekaligus
    await asyncio.gather(
        site.start(),
        game.game_loop(),
        client.start()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Server dihentikan.")
