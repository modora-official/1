import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import HTMLResponse, JSONResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, LikeEvent, GiftEvent, ShareEvent, ConnectEvent
import uvicorn

app = FastAPI()
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

# --- PWA CONFIGURATION ---
@app.get("/manifest.json")
async def get_manifest():
    return JSONResponse({
        "name": "Cyber Defense Pro", "short_name": "CyberDef", "start_url": "/",
        "display": "fullscreen", "orientation": "landscape",
        "background_color": "#000000", "theme_color": "#ff003c",
        "icons": [{"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml"}]
    })

@app.get("/sw.js")
async def get_sw():
    return Response(content="self.addEventListener('install', (e)=>{self.skipWaiting();});", media_type="application/javascript")

@app.get("/icon.svg")
async def get_icon():
    return Response(content="""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="#000"/><text x="50%" y="50%" fill="#ff003c" font-size="250" font-family="Arial" dominant-baseline="middle" text-anchor="middle">☢️</text></svg>""", media_type="image/svg+xml")

# --- MASSIVE FRONTEND PAYLOAD (UI/UX DEWA) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>CYBER DEFENSE COMMAND</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Teko:wght@400;600;700&display=swap');
        
        :root {
            --primary: #00f0ff; --danger: #ff003c; --warn: #fcee0a;
            --bg: #050505; --panel: rgba(0, 20, 30, 0.6);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg); color: var(--primary); font-family: 'Share Tech Mono', monospace;
            overflow: hidden; width: 100vw; height: 100vh; user-select: none;
            display: flex; justify-content: center; align-items: center;
        }

        /* Container 4:3 absolute lock */
        #core-system {
            width: 100vw; height: 100vh; max-width: 133.33vh; max-height: 75vw; aspect-ratio: 4/3;
            position: relative; background: radial-gradient(circle at center, #0a1118 0%, #000 100%);
            border: 1px solid var(--primary); box-shadow: inset 0 0 100px rgba(0, 240, 255, 0.1);
            overflow: hidden;
        }

        /* CRT Scanline Effect */
        #core-system::before {
            content: " "; display: block; position: absolute; top: 0; left: 0; bottom: 0; right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 99; background-size: 100% 2px, 3px 100%; pointer-events: none;
        }

        canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }

        /* HUD Panels */
        .hud-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; display: flex; flex-direction: column; padding: 2%; pointer-events: none; }
        
        /* Top Bar */
        .top-bar { display: flex; justify-content: space-between; align-items: flex-start; height: 10%; border-bottom: 2px solid rgba(0,240,255,0.3); padding-bottom: 10px; }
        .sys-title { font-family: 'Teko', sans-serif; font-size: 3rem; font-weight: 700; line-height: 0.8; letter-spacing: 2px; text-shadow: 0 0 10px var(--primary); }
        .sys-sub { font-size: 0.9rem; color: #888; }
        .status-box { text-align: right; }
        .pulse { display: inline-block; width: 10px; height: 10px; background: var(--danger); border-radius: 50%; box-shadow: 0 0 10px var(--danger); animation: blink 1s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        /* Main Content Grid */
        .main-grid { display: flex; justify-content: space-between; height: 90%; padding-top: 15px; gap: 20px; }
        
        .panel { background: var(--panel); border: 1px solid rgba(0,240,255,0.2); backdrop-filter: blur(4px); border-radius: 5px; display: flex; flex-direction: column; }
        .panel-header { background: rgba(0,240,255,0.15); padding: 5px 10px; font-weight: bold; font-family: 'Teko'; font-size: 1.5rem; letter-spacing: 1px; border-bottom: 1px solid var(--primary); }
        
        /* Leaderboard (Left) */
        .leaderboard { width: 30%; height: 75%; }
        .lb-content { padding: 10px; overflow: hidden; display: flex; flex-direction: column; gap: 10px; }
        .lb-item { display: flex; align-items: center; background: rgba(0,0,0,0.5); border-left: 3px solid #444; padding: 5px; transition: all 0.3s; }
        .lb-item.rank-1 { border-color: var(--warn); background: linear-gradient(90deg, rgba(252, 238, 10, 0.1), transparent); }
        .lb-rank { font-size: 1.2rem; font-weight: bold; width: 30px; text-align: center; }
        .lb-info { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .lb-name { font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff;}
        .lb-score { font-size: 1.1rem; color: var(--primary); font-weight: bold; }

        /* Terminal (Right) */
        .terminal { width: 35%; height: 90%; align-self: flex-end; }
        .term-content { padding: 10px; overflow: hidden; display: flex; flex-direction: column; justify-content: flex-end; height: 100%; font-size: 0.85rem; }
        .log-entry { margin-bottom: 5px; line-height: 1.2; word-wrap: break-word; animation: typeIn 0.2s ease-out; }
        .log-time { color: #555; margin-right: 5px; }
        .log-like { color: var(--danger); text-shadow: 0 0 5px var(--danger); }
        .log-gift { color: var(--warn); text-shadow: 0 0 5px var(--warn); font-weight: bold; }
        @keyframes typeIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }

        /* Boot Sequence Overlay */
        #boot-screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; pointer-events: auto; }
        .boot-text { font-size: 1.5rem; color: var(--primary); margin-bottom: 20px; text-align: center; white-space: pre-wrap; }
        .btn-boot { padding: 15px 40px; font-family: 'Share Tech Mono'; font-size: 1.5rem; font-weight: bold; background: transparent; color: var(--danger); border: 2px solid var(--danger); cursor: pointer; transition: 0.3s; box-shadow: 0 0 15px rgba(255,0,60,0.4); text-transform: uppercase; }
        .btn-boot:hover, .btn-boot:active { background: var(--danger); color: #000; }
    </style>
</head>
<body>
    <div id="core-system">
        <canvas id="engine"></canvas>
        
        <div class="hud-layer">
            <div class="top-bar">
                <div>
                    <div class="sys-title">CYBER DEFENSE OS v9.4</div>
                    <div class="sys-sub">TARGET LOCK: c_poek | ENCRYPTION: ACTIVE</div>
                </div>
                <div class="status-box">
                    <div style="font-size: 1.2rem;">SYSTEM <span class="pulse"></span></div>
                    <div class="sys-sub" id="clock">00:00:00</div>
                </div>
            </div>

            <div class="main-grid">
                <div class="panel leaderboard">
                    <div class="panel-header">TOP COMMANDERS</div>
                    <div class="lb-content" id="lb-data"></div>
                </div>

                <div class="panel terminal">
                    <div class="panel-header">LIVE SATELLITE FEED</div>
                    <div class="term-content" id="term-data"></div>
                </div>
            </div>
        </div>

        <div id="boot-screen">
            <div class="boot-text" id="boot-log">MENUNGGU OTORISASI ADMIN...</div>
            <button class="btn-boot" onclick="startBootSequence()">[ INISIALISASI SISTEM ]</button>
        </div>
    </div>

    <script>
        // --- 1. CORE LOGIC & STATE ---
        class SystemState {
            constructor() {
                this.users = {};
                this.maxLogs = 20;
            }
            addPoints(username, pts) {
                if(!this.users[username]) this.users[username] = 0;
                this.users[username] += pts;
                this.updateUI();
            }
            updateUI() {
                const sorted = Object.entries(this.users).sort((a,b)=>b[1]-a[1]).slice(0, 5);
                const html = sorted.map((u, i) => {
                    let rankClass = i === 0 ? 'rank-1' : '';
                    let rankColor = i === 0 ? '#fcee0a' : 'inherit';
                    return `<div class="lb-item ${rankClass}">
                        <div class="lb-rank" style="color:${rankColor}">0${i+1}</div>
                        <div class="lb-info">
                            <div class="lb-name">@${u[0]}</div>
                            <div class="lb-score">${u[1]} PTS</div>
                        </div>
                    </div>`;
                }).join('');
                document.getElementById('lb-data').innerHTML = html;
            }
        }
        const SYS = new SystemState();

        // --- 2. TERMINAL LOGGING ---
        function addLog(htmlStr) {
            const term = document.getElementById('term-data');
            const time = new Date().toLocaleTimeString('en-US', {hour12:false});
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `<span class="log-time">[${time}]</span> ${htmlStr}`;
            term.appendChild(div);
            if(term.childNodes.length > 25) term.removeChild(term.firstChild);
        }

        // --- 3. CANVAS PARTICLE ENGINE (PHYSICS) ---
        const canvas = document.getElementById('engine');
        const ctx = canvas.getContext('2d');
        let width, height;
        let particles = [];

        function resize() {
            const rect = document.getElementById('core-system').getBoundingClientRect();
            width = canvas.width = rect.width;
            height = canvas.height = rect.height;
        }
        window.addEventListener('resize', resize);
        resize();

        class Particle {
            constructor(x, y, color, speed, type) {
                this.x = x; this.y = y; this.color = color;
                this.type = type; // 0=laser, 1=explosion
                const angle = Math.random() * Math.PI * 2;
                this.vx = Math.cos(angle) * speed;
                this.vy = Math.sin(angle) * speed;
                this.life = 1.0;
                this.decay = type === 0 ? 0.02 : 0.005; // explosion lasts longer
                this.size = type === 0 ? 2 : Math.random() * 5 + 2;
            }
            update() {
                this.x += this.vx; this.y += this.vy;
                this.life -= this.decay;
                if(this.type === 1) this.size += 0.5; // expand explosion
            }
            draw() {
                ctx.globalAlpha = Math.max(0, this.life);
                ctx.fillStyle = this.color;
                ctx.shadowBlur = 10;
                ctx.shadowColor = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI*2);
                ctx.fill();
                ctx.shadowBlur = 0; // reset
            }
        }

        function spawnEffect(type) {
            // center of the screen
            const cx = width / 2;
            const cy = height / 2 + 50; 
            if(type === 'like') {
                // shoot laser
                for(let i=0; i<10; i++) particles.push(new Particle(cx, cy, '#ff003c', Math.random()*10+5, 0));
            } else if(type === 'gift') {
                // huge explosion
                for(let i=0; i<80; i++) particles.push(new Particle(cx, cy, '#fcee0a', Math.random()*20, 1));
            }
        }

        function renderLoop() {
            ctx.clearRect(0, 0, width, height);
            
            // Draw center base
            ctx.globalAlpha = 0.5;
            ctx.strokeStyle = '#00f0ff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(width/2, height/2 + 50, 40, 0, Math.PI*2);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(width/2, height/2 + 50, 60, 0, Math.PI*2);
            ctx.setLineDash([5, 15]);
            ctx.stroke();
            ctx.setLineDash([]); // reset

            for(let i=particles.length-1; i>=0; i--) {
                const p = particles[i];
                p.update();
                if(p.life <= 0) particles.splice(i, 1);
                else p.draw();
            }
            requestAnimationFrame(renderLoop);
        }

        // --- 4. BOOT SEQUENCE ---
        async function startBootSequence() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen();
            if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(()=>{});
            
            const btn = document.querySelector('.btn-boot');
            const log = document.getElementById('boot-log');
            btn.style.display = 'none';
            
            const msgs = [
                "MEMUAT KERNEL...", "MENGHUBUNGKAN KE SATELIT TIKTOK...",
                "MEMBYPASS KEAMANAN...", "MEMUAT MODUL GRAFIS CANVAS...",
                "SISTEM SIAP."
            ];
            for(let m of msgs) {
                log.innerText += "\\n> " + m;
                await new Promise(r => setTimeout(r, 600)); // fake delay
            }
            
            document.getElementById('boot-screen').style.display = 'none';
            renderLoop(); // start engine
            setInterval(()=>{ document.getElementById('clock').innerText = new Date().toLocaleTimeString('en-US', {hour12:false}); }, 1000);
        }

        // --- 5. WEBSOCKET CONNECTION ---
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'like') {
                SYS.addPoints(data.user, 1);
                addLog(`<span class="log-like">ATTACK DETECTED</span>: <b>${data.user}</b> fired laser!`);
                spawnEffect('like');
            } 
            else if (data.type === 'gift') {
                SYS.addPoints(data.user, 100);
                addLog(`<span class="log-gift">NUCLEAR LAUNCH</span>: <b>${data.user}</b> sent <b>${data.gift}</b>!`);
                spawnEffect('gift');
            }
            else if (data.type === 'comment') {
                addLog(`MSG: <b>${data.user}</b> > ${data.text}`);
            }
            else if (data.type === 'share') {
                addLog(`<span style="color:#00f0ff">RADAR PING</span>: <b>${data.user}</b> shared the feed!`);
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
async def on_connect(event: ConnectEvent): print("CONNECTED TO TIKTOK SATELLITE")

@client.on(LikeEvent)
async def on_like(event: LikeEvent): await broadcast({"type": "like", "user": event.user.unique_id})

@client.on(GiftEvent)
async def on_gift(event: GiftEvent): await broadcast({"type": "gift", "user": event.user.unique_id, "gift": event.gift.info.name})

@client.on(CommentEvent)
async def on_comment(event: CommentEvent): await broadcast({"type": "comment", "user": event.user.unique_id, "text": event.comment})

@client.on(ShareEvent)
async def on_share(event: ShareEvent): await broadcast({"type": "share", "user": event.user.unique_id})

async def start_tiktok():
    while True:
        try: await client.start()
        except Exception: await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    print("=========================================")
    print("☢️ CYBER DEFENSE PRO SERVER RUNNING ☢️")
    print("Buka Chrome: http://127.0.0.1:8000")
    print("=========================================")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")