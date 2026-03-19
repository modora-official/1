import asyncio
import json
from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import HTMLResponse, JSONResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
import uvicorn

app = FastAPI()
# Target username TikTok
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

# --- PWA CONFIGURATION ---
@app.get("/manifest.json")
async def get_manifest():
    manifest = {
        "name": "Live TikTok Racing",
        "short_name": "LiveRacing",
        "start_url": "/",
        "display": "standalone",
        "orientation": "landscape",
        "background_color": "#111111",
        "theme_color": "#ff0050",
        "icons": [{"src": "/icon.svg", "sizes": "192x192 512x512", "type": "image/svg+xml", "purpose": "any maskable"}]
    }
    return JSONResponse(manifest)

@app.get("/sw.js")
async def get_sw():
    js = """
    self.addEventListener('install', (e) => { self.skipWaiting(); });
    self.addEventListener('activate', (e) => { e.waitUntil(clients.claim()); });
    self.addEventListener('fetch', (e) => { });
    """
    return Response(content=js, media_type="application/javascript")

@app.get("/icon.svg")
async def get_icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="#111" rx="100"/><text x="50%" y="50%" fill="white" font-size="250" font-family="Arial" dominant-baseline="middle" text-anchor="middle">🏎️</text></svg>"""
    return Response(content=svg, media_type="image/svg+xml")

# --- FRONTEND HTML + CSS + JS ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Live Racing - c_poek</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#ff0050">
    <link rel="apple-touch-icon" href="/icon.svg">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,800;1,900&display=swap');
        body { 
            margin: 0; padding: 0; background-color: #050505; display: flex; 
            justify-content: center; align-items: center; height: 100vh; 
            overflow: hidden; font-family: 'Montserrat', sans-serif; color: white;
            user-select: none;
        }
        
        /* Container Rasio 4:3 */
        #game-container { 
            width: 100vw; max-width: 133.33vh; height: 100vh; max-height: 75vw; 
            background: #111; position: relative; aspect-ratio: 4 / 3; 
            display: flex; flex-direction: column; overflow: hidden;
            box-shadow: 0 0 30px rgba(0,0,0,1);
        }

        /* Top HUD */
        .header {
            height: 15%; background: linear-gradient(to bottom, #000, transparent);
            display: flex; justify-content: space-between; align-items: center;
            padding: 0 5%; z-index: 10;
        }
        .team-hud { text-align: center; text-transform: uppercase; }
        .team-kiri { color: #00e5ff; text-shadow: 0 0 10px #00e5ff; }
        .team-kanan { color: #ff0050; text-shadow: 0 0 10px #ff0050; }
        .hud-title { font-size: 1.5rem; letter-spacing: 2px; }
        .hud-score { font-size: 3rem; font-weight: 900; line-height: 1; }

        /* The Road */
        .track-container {
            flex-grow: 1; position: relative; background: #222;
            border-top: 5px solid #555; border-bottom: 5px solid #555;
            overflow: hidden; display: flex; flex-direction: column;
        }
        
        /* Moving Road Effect */
        .road-lines {
            position: absolute; top: 0; left: 0; width: 200%; height: 100%;
            background: repeating-linear-gradient(90deg, transparent 0, transparent 40px, rgba(255,255,255,0.2) 40px, rgba(255,255,255,0.2) 80px);
            background-size: 80px 10px; background-position: center; background-repeat: repeat-x;
            animation: moveRoad 1s linear infinite; z-index: 1;
        }
        @keyframes moveRoad { from { transform: translateX(0); } to { transform: translateX(-80px); } }

        /* Finish Line */
        .finish-line {
            position: absolute; right: 5%; top: 0; width: 40px; height: 100%;
            background: repeating-conic-gradient(#000 0% 25%, #fff 0% 50%) 50% / 20px 20px;
            z-index: 2; border-left: 5px solid #ffd700;
        }

        /* Lanes */
        .lane { flex: 1; position: relative; z-index: 3; display: flex; align-items: center; border-bottom: 2px dashed rgba(255,255,255,0.1); }
        .lane:last-child { border-bottom: none; }

        /* Cars */
        .car-wrapper {
            position: absolute; left: 2%; transition: left 0.2s ease-out;
            display: flex; flex-direction: column; align-items: center;
            filter: drop-shadow(5px 5px 10px rgba(0,0,0,0.8));
        }
        .car { font-size: 5rem; line-height: 1; transform: scaleX(-1); } /* Flip emoji memutar ke kanan */
        .car-name { font-size: 1rem; font-weight: 900; background: rgba(0,0,0,0.7); padding: 2px 8px; border-radius: 5px; margin-top: -10px;}
        .kiri-name { color: #00e5ff; border: 1px solid #00e5ff; }
        .kanan-name { color: #ff0050; border: 1px solid #ff0050; }

        /* Bottom Controls/Info */
        .footer {
            height: 15%; background: linear-gradient(to top, #000, transparent);
            display: flex; justify-content: center; align-items: center; flex-direction: column; z-index: 10;
        }
        .instruction { font-size: 1.8rem; font-weight: 900; }
        .instruction span.kiri { color: #00e5ff; }
        .instruction span.kanan { color: #ff0050; }

        /* Menus & Modals */
        #menu-overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); backdrop-filter: blur(5px);
            display: flex; justify-content: center; align-items: center; flex-direction: column;
            z-index: 100; gap: 20px;
        }
        .btn {
            padding: 15px 40px; font-size: 1.5rem; font-weight: 900; color: white;
            border: none; border-radius: 50px; cursor: pointer; text-transform: uppercase;
            box-shadow: 0 5px 15px rgba(0,0,0,0.5); transition: transform 0.1s;
        }
        .btn:active { transform: scale(0.95); }
        .btn-play { background: linear-gradient(45deg, #00e5ff, #0055ff); }
        .btn-install { background: linear-gradient(45deg, #ff0050, #88002a); display: none; }

        #winner-banner {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0);
            background: linear-gradient(45deg, #ffd700, #ff8c00); color: black;
            padding: 20px 50px; border-radius: 20px; font-size: 3rem; font-weight: 900;
            text-align: center; z-index: 50; box-shadow: 0 0 50px #ffd700;
            transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
    </style>
</head>
<body>
    <div id="game-container">
        <div id="menu-overlay">
            <h1 style="font-size: 3rem; margin:0; text-shadow: 0 0 20px #fff; text-align: center;">TIKTOK RACING</h1>
            <button class="btn btn-play" onclick="startGame()">Mulai Layar Penuh</button>
            <button class="btn btn-install" id="installBtn">Install Game (PWA)</button>
        </div>

        <div id="winner-banner">TIM MENANG!</div>

        <div class="header">
            <div class="team-hud team-kiri">
                <div class="hud-title">TIM KIRI</div>
                <div class="hud-score" id="score-kiri">0%</div>
            </div>
            <div class="team-hud team-kanan">
                <div class="hud-title">TIM KANAN</div>
                <div class="hud-score" id="score-kanan">0%</div>
            </div>
        </div>

        <div class="track-container">
            <div class="road-lines"></div>
            <div class="finish-line"></div>
            
            <div class="lane">
                <div class="car-wrapper" id="car-kiri">
                    <div class="car">🏎️</div>
                    <div class="car-name kiri-name">KIRI</div>
                </div>
            </div>
            <div class="lane">
                <div class="car-wrapper" id="car-kanan">
                    <div class="car">🏎️</div>
                    <div class="car-name kanan-name">KANAN</div>
                </div>
            </div>
        </div>

        <div class="footer">
            <div class="instruction">Ketik <span class="kiri">KIRI</span> atau <span class="kanan">KANAN</span> di Komentar!</div>
        </div>
    </div>

    <script>
        // PWA Setup
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').then(() => console.log("SW Registered"));
        }

        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            document.getElementById('installBtn').style.display = 'block';
        });

        document.getElementById('installBtn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') { document.getElementById('installBtn').style.display = 'none'; }
                deferredPrompt = null;
            }
        });

        // Game Logic
        let progressKiri = 2; // Start at 2% padding
        let progressKanan = 2;
        let isRacing = false;
        const WIN_TARGET = 85; // 85% is hitting the finish line visual

        function startGame() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) { elem.requestFullscreen(); }
            else if (elem.webkitRequestFullscreen) { elem.webkitRequestFullscreen(); }
            
            if (screen.orientation && screen.orientation.lock) {
                screen.orientation.lock('landscape').catch(() => console.log("Orientation lock failed"));
            }
            
            document.getElementById('menu-overlay').style.display = 'none';
            resetGame();
            isRacing = true;
        }

        function resetGame() {
            progressKiri = 2; progressKanan = 2;
            updateUI();
            document.getElementById('winner-banner').style.transform = 'translate(-50%, -50%) scale(0)';
            isRacing = true;
        }

        function showWinner(team) {
            isRacing = false;
            const banner = document.getElementById('winner-banner');
            banner.innerHTML = `🏁 TIM ${team} MENANG! 🏁<br><span style="font-size:1.5rem">Mulai ulang dalam 5 detik...</span>`;
            banner.style.transform = 'translate(-50%, -50%) scale(1)';
            setTimeout(resetGame, 5000);
        }

        // WebSockets
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = function(event) {
            if(!isRacing) return;
            const data = JSON.parse(event.data);
            const comment = data.comment.toUpperCase().trim();
            
            // Movement Step per comment (Atur kecepatan di sini)
            const step = 1.5; 

            if (comment === 'KIRI') { progressKiri += step; } 
            else if (comment === 'KANAN') { progressKanan += step; }
            
            updateUI();

            if (progressKiri >= WIN_TARGET) { showWinner('KIRI (BIRU)'); }
            else if (progressKanan >= WIN_TARGET) { showWinner('KANAN (MERAH)'); }
        };

        function updateUI() {
            // Cap at finish line
            let visKiri = Math.min(progressKiri, WIN_TARGET);
            let visKanan = Math.min(progressKanan, WIN_TARGET);

            document.getElementById('car-kiri').style.left = visKiri + '%';
            document.getElementById('car-kanan').style.left = visKanan + '%';
            
            // Calculate percentage based on track length
            let pctKiri = Math.floor(((progressKiri - 2) / (WIN_TARGET - 2)) * 100);
            let pctKanan = Math.floor(((progressKanan - 2) / (WIN_TARGET - 2)) * 100);
            
            document.getElementById('score-kiri').innerText = Math.max(0, Math.min(100, pctKiri)) + '%';
            document.getElementById('score-kanan').innerText = Math.max(0, Math.min(100, pctKanan)) + '%';
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(HTML_CONTENT)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_websockets.remove(websocket)

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    message = json.dumps({"user": event.user.unique_id, "comment": event.comment})
    for ws in connected_websockets.copy():
        try:
            await ws.send_text(message)
        except:
            pass

async def start_tiktok():
    try:
        # Loop agar tidak crash saat TikTok offline
        while True:
            try:
                await client.start()
            except Exception as e:
                print(f"Mencoba konek ulang ke TikTok... ({e})")
                await asyncio.sleep(5)
    except Exception:
        pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    print("🚀 SERVER GAME BALAPAN BERJALAN! Buka http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
