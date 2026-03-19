import asyncio
import json
from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import HTMLResponse, JSONResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, LikeEvent, GiftEvent, ConnectEvent
import uvicorn

app = FastAPI()
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

@app.get("/manifest.json")
async def get_manifest():
    return JSONResponse({
        "name": "Live Command Center", "short_name": "WarRoom", "start_url": "/",
        "display": "standalone", "orientation": "landscape",
        "background_color": "#050b14", "theme_color": "#00ffea"
    })

# --- FRONTEND (UI HIGH-TECH & TOP USER LOGIC) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>War Command Center</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;700&display=swap');
        
        * { box-sizing: border-box; }
        body { 
            margin: 0; padding: 0; background: #02050a; color: white;
            font-family: 'Rajdhani', sans-serif; overflow: hidden; user-select: none;
            display: flex; justify-content: center; align-items: center; height: 100vh;
        }

        /* Container 4:3 */
        #game-wrapper {
            width: 100vw; height: 100vh; max-width: 133.33vh; max-height: 75vw; aspect-ratio: 4/3;
            background: radial-gradient(circle at center, #0a192f 0%, #02050a 100%);
            position: relative; overflow: hidden; border: 2px solid #00ffea;
            box-shadow: inset 0 0 50px rgba(0, 255, 234, 0.2), 0 0 20px rgba(0, 255, 234, 0.5);
        }

        /* Radar Grid Background */
        .grid {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: 
                linear-gradient(rgba(0, 255, 234, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 234, 0.1) 1px, transparent 1px);
            background-size: 30px 30px; z-index: 1; pointer-events: none;
        }

        /* Canvas Particle Engine */
        #particle-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 2; }

        /* HUD LAYOUT */
        #hud-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; display: flex; flex-direction: column; padding: 15px; }

        .header { display: flex; justify-content: space-between; align-items: flex-start; }
        .title-box { background: rgba(0, 20, 40, 0.8); border-left: 5px solid #00ffea; padding: 10px 20px; backdrop-filter: blur(5px); }
        .title-box h1 { font-family: 'Orbitron', sans-serif; margin: 0; font-size: 1.8rem; color: #00ffea; text-shadow: 0 0 10px #00ffea; }
        .title-box p { margin: 0; color: #8892b0; font-size: 1rem; }

        /* TOP USER LEADERBOARD (KIRI) */
        .panel {
            background: rgba(2, 10, 20, 0.85); border: 1px solid rgba(0, 255, 234, 0.3);
            border-radius: 8px; backdrop-filter: blur(10px); display: flex; flex-direction: column;
        }
        
        #top-users { width: 35%; height: 60%; margin-top: 15px; position: absolute; left: 15px; top: 70px; }
        .panel-header { background: rgba(0, 255, 234, 0.1); padding: 8px 15px; border-bottom: 1px solid rgba(0, 255, 234, 0.3); font-family: 'Orbitron'; font-weight: bold; color: #ffd700; display: flex; align-items: center; gap: 10px; }
        .panel-body { padding: 10px; flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 8px; }

        .user-card {
            display: flex; justify-content: space-between; align-items: center;
            background: linear-gradient(90deg, rgba(0,255,234,0.1), transparent);
            padding: 8px 12px; border-radius: 4px; border-left: 3px solid #888;
            transition: all 0.3s ease;
        }
        .user-card.rank-1 { border-left-color: #ffd700; background: linear-gradient(90deg, rgba(255, 215, 0, 0.2), transparent); box-shadow: 0 0 10px rgba(255,215,0,0.2); }
        .user-card.rank-2 { border-left-color: #c0c0c0; }
        .user-card.rank-3 { border-left-color: #cd7f32; }
        
        .user-info { display: flex; align-items: center; gap: 10px; }
        .user-rank { font-family: 'Orbitron'; font-weight: 900; font-size: 1.2rem; }
        .user-name { font-size: 1.1rem; font-weight: bold; color: white; width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .user-score { font-family: 'Orbitron'; color: #00ffea; font-size: 1.1rem; font-weight: bold; }

        /* NOTIFICATION LOG (KANAN BAWAH) */
        #activity-log { width: 40%; height: 40%; position: absolute; right: 15px; bottom: 15px; }
        #log-content { display: flex; flex-direction: column; gap: 5px; font-size: 0.95rem; justify-content: flex-end; }
        .log-item { padding: 5px 10px; border-radius: 3px; animation: slideLeft 0.3s ease-out; border-left: 2px solid; }
        .log-like { background: rgba(255, 0, 80, 0.1); border-color: #ff0050; color: #ffb3c6; }
        .log-gift { background: rgba(255, 215, 0, 0.1); border-color: #ffd700; color: #fff3b0; font-weight: bold; }
        .log-join { background: rgba(0, 255, 234, 0.1); border-color: #00ffea; color: #a6fff8; }

        @keyframes slideLeft { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

        /* Start Overlay */
        #start-overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 100;
            background: rgba(0,0,0,0.9); display: flex; flex-direction: column; justify-content: center; align-items: center;
        }
        .btn { padding: 15px 40px; font-size: 1.5rem; background: transparent; color: #00ffea; border: 2px solid #00ffea; cursor: pointer; border-radius: 5px; font-family: 'Orbitron'; font-weight: bold; text-transform: uppercase; transition: all 0.2s; box-shadow: 0 0 15px rgba(0,255,234,0.3); }
        .btn:active { background: #00ffea; color: black; }
    </style>
</head>
<body>
    <div id="game-wrapper">
        <div class="grid"></div>
        <canvas id="particle-canvas"></canvas>

        <div id="hud-container">
            <div class="header">
                <div class="title-box">
                    <h1>SISTEM PERTAHANAN CYBER</h1>
                    <p>STATUS: AKTIF | TARGET: c_poek</p>
                </div>
            </div>

            <div class="panel" id="top-users">
                <div class="panel-header">👑 TOP KOMANDAN (PENYUMBANG)</div>
                <div class="panel-body" id="leaderboard-body">
                    </div>
            </div>

            <div class="panel" id="activity-log">
                <div class="panel-header">📡 RADAR AKTIVITAS</div>
                <div class="panel-body" id="log-content"></div>
            </div>
        </div>

        <div id="start-overlay">
            <button class="btn" onclick="initSystem()">INISIALISASI SISTEM</button>
        </div>
    </div>

    <script>
        // --- DATA & LOGIC MANAGER ---
        let topUsers = {}; // Simpan skor user: { username: { score: 100, name: 'Budi' } }
        const POINT_LIKE = 1;
        const POINT_GIFT = 100; // Gift nilainya jauh lebih besar
        let isSystemActive = false;

        function initSystem() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen();
            if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(()=>{});
            document.getElementById('start-overlay').style.display = 'none';
            initParticles();
            isSystemActive = true;
        }

        function updateScore(username, points) {
            if (!topUsers[username]) topUsers[username] = { score: 0, name: username };
            topUsers[username].score += points;
            renderLeaderboard();
        }

        function renderLeaderboard() {
            // Urutkan dari tertinggi ke terendah, ambil top 5
            const sorted = Object.values(topUsers).sort((a, b) => b.score - a.score).slice(0, 5);
            const container = document.getElementById('leaderboard-body');
            
            container.innerHTML = sorted.map((user, index) => {
                let rankClass = index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : '';
                let rankColor = index === 0 ? '#ffd700' : index === 1 ? '#c0c0c0' : index === 2 ? '#cd7f32' : '#888';
                
                return `
                <div class="user-card ${rankClass}">
                    <div class="user-info">
                        <span class="user-rank" style="color:${rankColor}">#${index + 1}</span>
                        <span class="user-name">@${user.name}</span>
                    </div>
                    <span class="user-score">${user.score.toLocaleString()} PT</span>
                </div>
                `;
            }).join('');
        }

        function addLog(text, typeClass) {
            const log = document.getElementById('log-content');
            const el = document.createElement('div');
            el.className = `log-item ${typeClass}`;
            el.innerHTML = text;
            log.appendChild(el);
            if (log.children.length > 7) log.removeChild(log.firstChild);
        }

        // --- VISUAL ENGINE (CANVAS PARTICLES) ---
        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        let particles = [];

        function resizeCanvas() {
            canvas.width = document.getElementById('game-wrapper').clientWidth;
            canvas.height = document.getElementById('game-wrapper').clientHeight;
        }
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        class Particle {
            constructor(x, y, color, speed, size) {
                this.x = x; this.y = y; this.color = color;
                this.vx = (Math.random() - 0.5) * speed;
                this.vy = (Math.random() - 0.5) * speed;
                this.life = 1.0; this.decay = Math.random() * 0.02 + 0.01;
                this.size = size;
            }
            update() {
                this.x += this.vx; this.y += this.vy; this.life -= this.decay;
            }
            draw() {
                ctx.globalAlpha = this.life;
                ctx.fillStyle = this.color;
                ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fill();
            }
        }

        function triggerExplosion(color, amount, speed, size) {
            const x = canvas.width / 2 + (Math.random() * 200 - 100);
            const y = canvas.height / 2 + (Math.random() * 100 - 50);
            for(let i=0; i<amount; i++) particles.push(new Particle(x, y, color, speed, size));
        }

        function initParticles() {
            requestAnimationFrame(animate);
        }

        function animate() {
            if(!isSystemActive) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            for (let i = particles.length - 1; i >= 0; i--) {
                particles[i].update(); particles[i].draw();
                if (particles[i].life <= 0) particles.splice(i, 1);
            }
            requestAnimationFrame(animate);
        }

        // --- WEBSOCKET CONNECTION ---
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
            if (!isSystemActive) return;
            const data = JSON.parse(event.data);
            
            if (data.type === 'like') {
                updateScore(data.user, POINT_LIKE);
                addLog(`[LIKE] <b>${data.user}</b> menembakkan laser!`, 'log-like');
                triggerExplosion('#ff0050', 5, 5, 2); // Ledakan kecil
            } 
            else if (data.type === 'gift') {
                updateScore(data.user, POINT_GIFT);
                addLog(`[GIFT] <b>${data.user}</b> mengirim ${data.gift}!`, 'log-gift');
                triggerExplosion('#ffd700', 50, 15, 4); // Ledakan besar emas
            }
            else if (data.type === 'comment') {
                if (Math.random() > 0.8) {
                    addLog(`[MSG] <b>${data.user}</b>: ${data.text}`, 'log-join');
                }
            }
        };
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

async def broadcast(message: dict):
    msg_str = json.dumps(message)
    for ws in connected_websockets.copy():
        try: await ws.send_text(msg_str)
        except: pass

@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent): print("Terhubung ke TikTok!")

@client.on(LikeEvent)
async def on_like(event: LikeEvent):
    await broadcast({"type": "like", "user": event.user.unique_id})

@client.on(GiftEvent)
async def on_gift(event: GiftEvent):
    await broadcast({"type": "gift", "user": event.user.unique_id, "gift": event.gift.info.name})

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    await broadcast({"type": "comment", "user": event.user.unique_id, "text": event.comment})

async def start_tiktok():
    while True:
        try: await client.start()
        except Exception: await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")