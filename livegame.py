import asyncio
import json
from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import HTMLResponse, JSONResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
import uvicorn

app = FastAPI()
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

# --- PWA CONFIG ---
@app.get("/manifest.json")
async def get_manifest():
    return JSONResponse({
        "name": "Live Flag Race", "short_name": "FlagRace", "start_url": "/",
        "display": "standalone", "orientation": "landscape",
        "background_color": "#0a0a0a", "theme_color": "#00ff88",
        "icons": [{"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any"}]
    })

@app.get("/sw.js")
async def get_sw():
    js = "self.addEventListener('install', (e) => { self.skipWaiting(); }); self.addEventListener('activate', (e) => { e.waitUntil(clients.claim()); }); self.addEventListener('fetch', (e) => { });"
    return Response(content=js, media_type="application/javascript")

@app.get("/icon.svg")
async def get_icon():
    return Response(content="""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="#0a0a0a"/><text x="50%" y="50%" fill="white" font-size="250" font-family="Arial" dominant-baseline="middle" text-anchor="middle">🌍</text></svg>""", media_type="image/svg+xml")

# --- FRONTEND (UI/UX DEWA) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Flag Race Live</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;800;900&display=swap');
        
        * { box-sizing: border-box; }
        body {
            margin: 0; padding: 0; background: #000; display: flex;
            justify-content: center; align-items: center; height: 100vh; width: 100vw;
            font-family: 'Poppins', sans-serif; overflow: hidden; user-select: none;
        }

        /* Container 4:3 Presisi - Anti Potong */
        #game-wrapper {
            width: 100%; height: 100%; max-width: 133.33vh; max-height: 75vw;
            aspect-ratio: 4/3; background: radial-gradient(circle at top, #1a1a2e 0%, #0f0f1a 100%);
            position: relative; display: flex; flex-direction: column; padding: 20px;
            box-shadow: 0 0 50px rgba(0, 255, 136, 0.1); border-radius: 15px; overflow: hidden;
        }

        .header {
            text-align: center; color: white; margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(255,255,255,0.5);
        }
        .header h1 { margin: 0; font-size: 2.5rem; font-weight: 900; letter-spacing: 2px; color: #00ff88; text-transform: uppercase;}
        .header p { margin: 0; font-size: 1.2rem; opacity: 0.8; }

        /* Leaderboard Container */
        #leaderboard {
            flex: 1; display: flex; flex-direction: column; gap: 15px; justify-content: center;
        }

        /* Bar Item */
        .bar-container {
            display: flex; align-items: center; background: rgba(255, 255, 255, 0.05);
            padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(5px); transform: translateY(0); transition: all 0.4s ease;
        }
        
        .rank { font-size: 1.5rem; color: #888; width: 40px; font-weight: 900; }
        .flag { font-size: 2.5rem; margin-right: 15px; filter: drop-shadow(0 0 5px rgba(0,0,0,0.5)); }
        
        .progress-wrapper {
            flex: 1; height: 35px; background: rgba(0,0,0,0.5); border-radius: 20px;
            overflow: hidden; position: relative; border: 1px solid #333;
        }
        
        .progress-fill {
            height: 100%; background: linear-gradient(90deg, #00ff88, #00b3ff);
            width: 3%; /* Default minimal 3% */
            border-radius: 20px; transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.6);
            display: flex; align-items: center; justify-content: flex-end; padding-right: 10px;
        }

        .score-text { color: white; font-weight: 900; font-size: 1rem; text-shadow: 1px 1px 2px #000; }

        /* Overlay PWA / Start */
        #overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); z-index: 100; display: flex; flex-direction: column;
            justify-content: center; align-items: center; gap: 20px;
        }
        .btn {
            padding: 15px 30px; font-size: 1.2rem; font-weight: bold; color: #000;
            background: #00ff88; border: none; border-radius: 30px; cursor: pointer;
            text-transform: uppercase; box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }
        #btn-install { background: #ff0050; color: white; box-shadow: 0 0 20px rgba(255, 0, 80, 0.5); display: none; }
    </style>
</head>
<body>
    <div id="game-wrapper">
        <div id="overlay">
            <button class="btn" onclick="startPro()">Mulai Fullscreen Profesional</button>
            <button class="btn" id="btn-install">Install Aplikasi (PWA)</button>
        </div>

        <div class="header">
            <h1>🌍 PERANG BENDERA NEGARA</h1>
            <p>Kirim Emoji Bendera di Komentar untuk Mendukung Negaramu!</p>
        </div>

        <div id="leaderboard">
            </div>
    </div>

    <script>
        // PWA Script
        if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault(); deferredPrompt = e;
            document.getElementById('btn-install').style.display = 'block';
        });
        document.getElementById('btn-install').addEventListener('click', async () => {
            if (deferredPrompt) { deferredPrompt.prompt(); deferredPrompt = null; }
        });

        // Mode Layar Penuh (Anti-Crop)
        function startPro() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen();
            if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(()=>{});
            document.getElementById('overlay').style.display = 'none';
        }

        // Logic Game
        // Default Top 6, minimal 3%
        let countryData = {
            "🇮🇩": 3, "🇲🇾": 3, "🇸🇬": 3, "🇹🇭": 3, "🇵🇭": 3, "🇯🇵": 3
        };
        const maxScore = 500; // Cap batas penuh layar

        // Regex pendeteksi semua emoji bendera negara
        const flagRegex = /[\\uD83C][\\uDDE6-\\uDDFF][\\uD83C][\\uDDE6-\\uDDFF]/g;

        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const flags = data.comment.match(flagRegex);
            
            if (flags) {
                // Hapus duplikat dalam 1 komentar agar adil
                const uniqueFlags = [...new Set(flags)];
                uniqueFlags.forEach(flag => {
                    if (!countryData[flag]) countryData[flag] = 3; // Jika baru, mulai dari 3%
                    countryData[flag] += 1;
                });
                renderUI();
            }
        };

        function renderUI() {
            // Urutkan berdasarkan skor tertinggi, ambil Top 6
            const sorted = Object.entries(countryData).sort((a, b) => b[1] - a[1]).slice(0, 6);
            const container = document.getElementById('leaderboard');
            
            // Animasi referesh ringan
            container.innerHTML = sorted.map((item, index) => {
                const flag = item[0];
                const score = item[1];
                // Hitung persen lebar (minimal 3%)
                const widthPercent = Math.min(100, Math.max(3, (score / maxScore) * 100));
                
                // Efek warna emas untuk juara 1
                const rankColor = index === 0 ? '#ffd700' : '#888';
                
                return `
                <div class="bar-container">
                    <div class="rank" style="color: ${rankColor}">#${index + 1}</div>
                    <div class="flag">${flag}</div>
                    <div class="progress-wrapper">
                        <div class="progress-fill" style="width: ${widthPercent}%">
                            <span class="score-text">${score}</span>
                        </div>
                    </div>
                </div>
                `;
            }).join('');
        }

        // Initial render
        renderUI();
    </script>
</body>
</html>
"""

@app.get("/")
async def root(): return HTMLResponse(HTML_CONTENT)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True: await websocket.receive_text()
    except:
        connected_websockets.remove(websocket)

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    msg = json.dumps({"comment": event.comment})
    for ws in connected_websockets.copy():
        try: await ws.send_text(msg)
        except: pass

async def start_tiktok():
    while True:
        try: await client.start()
        except Exception: await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    print("🔥 MODE DEWA AKTIF! Buka http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")