import asyncio
import json
from fastapi import FastAPI, WebSocket, Response
from fastapi.responses import HTMLResponse, JSONResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, LikeEvent, GiftEvent, ShareEvent, ConnectEvent
import uvicorn

app = FastAPI()
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

# --- PWA CONFIG ---
@app.get("/manifest.json")
async def get_manifest():
    return JSONResponse({
        "name": "Live 3D War", "short_name": "3DWar", "start_url": "/",
        "display": "standalone", "orientation": "landscape",
        "background_color": "#000000", "theme_color": "#ff0000",
        "icons": [{"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml"}]
    })

@app.get("/sw.js")
async def get_sw():
    js = "self.addEventListener('install', (e) => { self.skipWaiting(); });"
    return Response(content=js, media_type="application/javascript")

@app.get("/icon.svg")
async def get_icon():
    return Response(content="""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" fill="#000"/><text x="50%" y="50%" fill="red" font-size="250" font-family="Arial" dominant-baseline="middle" text-anchor="middle">🚀</text></svg>""", media_type="image/svg+xml")

# --- FRONTEND 3D (THREE.JS + HTML) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>3D Live War</title>
    <link rel="manifest" href="/manifest.json">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
        body { margin: 0; overflow: hidden; background: #000; font-family: 'Rajdhani', sans-serif; user-select: none; }
        
        #game-container {
            width: 100vw; height: 100vh; max-width: 133.33vh; max-height: 75vw;
            aspect-ratio: 4/3; margin: auto; position: relative; background: #050505;
            box-shadow: 0 0 50px rgba(255,0,0,0.2);
        }

        #canvas-container { width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 1; }

        /* UI Overlay Profesional */
        #ui-layer {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10;
            pointer-events: none; padding: 20px; box-sizing: border-box;
            background: radial-gradient(circle, transparent 60%, rgba(0,0,0,0.8) 100%);
        }

        .hud-title { color: #ff0050; font-size: 2rem; font-weight: 700; text-transform: uppercase; text-shadow: 0 0 10px #ff0050; margin: 0; }
        .hud-subtitle { color: #00e5ff; font-size: 1.2rem; margin: 0; text-shadow: 0 0 5px #00e5ff; }

        /* Notification Log */
        #notif-log {
            position: absolute; bottom: 20px; left: 20px; width: 40%; max-height: 40%;
            display: flex; flex-direction: column-reverse; gap: 8px; overflow: hidden;
        }
        .notif-item {
            background: rgba(0, 20, 40, 0.7); border-left: 4px solid #00e5ff;
            padding: 8px 12px; color: white; border-radius: 4px; font-size: 1.1rem;
            animation: slideIn 0.3s ease-out; backdrop-filter: blur(4px);
        }
        .notif-like { border-left-color: #ff0050; }
        .notif-gift { border-left-color: #ffd700; background: rgba(40, 30, 0, 0.8); font-weight: bold; }
        .notif-share { border-left-color: #00ff88; }
        
        @keyframes slideIn { from { transform: translateX(-50px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

        /* Start Button Overlay */
        #start-overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 100;
            background: rgba(0,0,0,0.9); display: flex; flex-direction: column; justify-content: center; align-items: center; pointer-events: auto;
        }
        .btn { padding: 15px 40px; font-size: 1.5rem; background: #ff0050; color: white; border: none; cursor: pointer; border-radius: 5px; font-family: 'Rajdhani'; font-weight: bold; text-transform: uppercase; box-shadow: 0 0 20px #ff0050; }
    </style>
</head>
<body>
    <div id="game-container">
        <div id="canvas-container"></div>
        
        <div id="ui-layer">
            <h1 class="hud-title">TARGET: KOTA MUSUH</h1>
            <p class="hud-subtitle">TAP LAYAR UNTUK MENEMBAK | GIFT UNTUK NUKLIR</p>
            <div id="notif-log"></div>
        </div>

        <div id="start-overlay">
            <h1 style="color:white; font-size:3rem; margin-bottom: 20px;">3D CYBER WARFARE</h1>
            <button class="btn" onclick="initGame()">Mulai Fullscreen</button>
        </div>
    </div>

    <script>
        // --- 3D ENGINE SETUP ---
        let scene, camera, renderer;
        let projectiles = [];
        let particles = [];
        let isRunning = false;

        function init3D() {
            const container = document.getElementById('canvas-container');
            scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2(0x000000, 0.02);

            // Camera rasio 4:3
            camera = new THREE.PerspectiveCamera(60, 4/3, 0.1, 1000);
            camera.position.set(0, 5, 20);
            camera.lookAt(0, 0, -30);

            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            // Lighting
            const ambient = new THREE.AmbientLight(0x222222);
            scene.add(ambient);
            const directional = new THREE.DirectionalLight(0xffffff, 1);
            directional.position.set(10, 20, 10);
            scene.add(directional);

            // Ground Grid (Matrix Style)
            const gridHelper = new THREE.GridHelper(200, 100, 0x00e5ff, 0x003344);
            gridHelper.position.y = -2;
            scene.add(gridHelper);

            // Enemy Target Box (The Base)
            const baseGeometry = new THREE.BoxGeometry(10, 10, 10);
            const baseMaterial = new THREE.MeshPhongMaterial({ color: 0x222222, emissive: 0x550000, wireframe: true });
            const enemyBase = new THREE.Mesh(baseGeometry, baseMaterial);
            enemyBase.position.set(0, 3, -40);
            scene.add(enemyBase);

            animate();
        }

        function createExplosion(x, y, z, color, size) {
            const geometry = new THREE.SphereGeometry(size, 16, 16);
            const material = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.8 });
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.set(x, y, z);
            scene.add(sphere);
            particles.push({ mesh: sphere, life: 1.0, decay: 0.05, maxScale: size * 2 });
        }

        function fireMissile(isGift = false) {
            const geometry = new THREE.CylinderGeometry(0.2, 0.2, 2, 8);
            geometry.rotateX(Math.PI / 2);
            const color = isGift ? 0xffd700 : 0xff0050; // Gold for gift, Red for like
            const material = new THREE.MeshBasicMaterial({ color: color });
            const missile = new THREE.Mesh(geometry, material);
            
            // Random start position near camera
            missile.position.set((Math.random() - 0.5) * 20, Math.random() * 5 + 1, 15);
            scene.add(missile);
            
            projectiles.push({ mesh: missile, speed: isGift ? 1.5 : 1.0, isGift: isGift });
        }

        function animate() {
            if (!isRunning) return;
            requestAnimationFrame(animate);

            // Move Projectiles
            for (let i = projectiles.length - 1; i >= 0; i--) {
                let p = projectiles[i];
                p.mesh.position.z -= p.speed;
                p.mesh.position.x *= 0.95; // Curve towards center
                
                // Hit Target
                if (p.mesh.position.z <= -35) {
                    createExplosion(
                        (Math.random() - 0.5) * 10, Math.random() * 5, -35 + (Math.random() * 5),
                        p.isGift ? 0xffaa00 : 0xff5555,
                        p.isGift ? 8 : 2
                    );
                    scene.remove(p.mesh);
                    projectiles.splice(i, 1);
                }
            }

            // Animate Explosions
            for (let i = particles.length - 1; i >= 0; i--) {
                let pt = particles[i];
                pt.life -= pt.decay;
                pt.mesh.scale.setScalar(1 + (1 - pt.life) * pt.maxScale);
                pt.mesh.material.opacity = pt.life;
                if (pt.life <= 0) {
                    scene.remove(pt.mesh);
                    particles.splice(i, 1);
                }
            }

            renderer.render(scene, camera);
        }

        // --- FULLSCREEN & UI SETUP ---
        function initGame() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen();
            if (screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(()=>{});
            
            document.getElementById('start-overlay').style.display = 'none';
            if(!scene) init3D();
            isRunning = true;
        }

        function addLog(text, typeClass) {
            const log = document.getElementById('notif-log');
            const el = document.createElement('div');
            el.className = `notif-item ${typeClass}`;
            el.innerHTML = text;
            log.prepend(el);
            if (log.children.length > 6) log.removeChild(log.lastChild); // Max 6 items
        }

        // --- WEBSOCKETS (TIKTOK DATA) ---
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
            if (!isRunning) return;
            const data = JSON.parse(event.data);
            
            if (data.type === 'like') {
                // Tembak 1 misil tiap ada notif like (bisa diatur)
                fireMissile();
                addLog(`🔥 <b>${data.user}</b> tap layar!`, 'notif-like');
            } 
            else if (data.type === 'gift') {
                // Tembak misil nuklir raksasa
                fireMissile(true);
                addLog(`🎁 <b>${data.user}</b> mengirim <b>${data.gift}</b>!`, 'notif-gift');
            }
            else if (data.type === 'share') {
                addLog(`↗️ <b>${data.user}</b> membagikan Live!`, 'notif-share');
            }
            else if (data.type === 'comment') {
                addLog(`💬 <b>${data.user}</b>: ${data.text}`, '');
            }
        };

        // Window resize handler to maintain 4:3 safely
        window.addEventListener('resize', () => {
            if(camera && renderer) {
                const container = document.getElementById('canvas-container');
                renderer.setSize(container.clientWidth, container.clientHeight);
            }
        });
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

# --- TIKTOK EVENTS ---
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print("Berhasil Terhubung ke TikTok Live!")

@client.on(LikeEvent)
async def on_like(event: LikeEvent):
    await broadcast({"type": "like", "user": event.user.unique_id, "amount": event.likeCount})

@client.on(GiftEvent)
async def on_gift(event: GiftEvent):
    await broadcast({"type": "gift", "user": event.user.unique_id, "gift": event.gift.info.name})

@client.on(ShareEvent)
async def on_share(event: ShareEvent):
    await broadcast({"type": "share", "user": event.user.unique_id})

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    await broadcast({"type": "comment", "user": event.user.unique_id, "text": event.comment})

async def start_tiktok():
    while True:
        try: await client.start()
        except Exception as e: 
            print("Mencoba konek ulang...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event(): asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    print("🔥 SERVER 3D CYBER WARFARE JALAN! Buka http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")