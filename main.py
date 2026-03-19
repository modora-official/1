import asyncio
import random
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
import uvicorn
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent, LikeEvent, JoinEvent, ShareEvent, ViewerCountUpdateEvent

# ==========================================
# KONFIGURASI GAME & TIKTOK
# ==========================================
TIKTOK_USERNAME = "c_poek"
WORDS = ["TERMUX", "PYTHON", "GITHUB", "TIKTOK", "STREAMING", "DEVELOPER", "WEBSITE", "SERVER", "CODING", "PROGRAMMER"]

app = FastAPI()

class GameState:
    def __init__(self):
        self.word = ""
        self.scrambled = ""
        self.top_users = {} # Format: {"username": score}
        self.stats = {"viewers": 0, "likes": 0, "shares": 0}
        self.next_word()

    def next_word(self):
        self.word = random.choice(WORDS)
        word_list = list(self.word)
        random.shuffle(word_list)
        self.scrambled = "".join(word_list)
        
    def guess(self, username: str, text: str) -> bool:
        if text.strip().upper() == self.word:
            if username in self.top_users:
                self.top_users[username] += 10
            else:
                self.top_users[username] = 10
            self.next_word()
            return True
        return False

    def get_top_3(self):
        sorted_users = sorted(self.top_users.items(), key=lambda x: x[1], reverse=True)[:3]
        return [{"username": k, "score": v} for k, v in sorted_users]

game = GameState()

# ==========================================
# WEBSOCKET MANAGER (KONEKSI FRONTEND)
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await self.broadcast_game_state()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

    async def broadcast_game_state(self):
        await self.broadcast("game_update", {
            "scrambled": game.scrambled,
            "top_users": game.get_top_3(),
            "stats": game.stats
        })

manager = ConnectionManager()
client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

# ==========================================
# EVENT HANDLER TIKTOK LIVE
# ==========================================
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    await manager.broadcast("system", {"message": f"Terhubung ke Live {TIKTOK_USERNAME}"})

@client.on(DisconnectEvent)
async def on_disconnect(event: DisconnectEvent):
    await manager.broadcast("system", {"message": "Koneksi terputus. Standby menunggu Live..."})

@client.on(ViewerCountUpdateEvent)
async def on_viewer_update(event: ViewerCountUpdateEvent):
    game.stats["viewers"] = event.viewer_count
    await manager.broadcast("stats_update", game.stats)

@client.on(LikeEvent)
async def on_like(event: LikeEvent):
    game.stats["likes"] += event.like_count
    await manager.broadcast("stats_update", game.stats)

@client.on(ShareEvent)
async def on_share(event: ShareEvent):
    game.stats["shares"] += 1
    await manager.broadcast("stats_update", game.stats)
    await manager.broadcast("notification", {"message": f"{event.user.nickname} membagikan Live!"})

@client.on(JoinEvent)
async def on_join(event: JoinEvent):
    await manager.broadcast("notification", {"message": f"{event.user.nickname} bergabung."})

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    username = event.user.nickname
    comment = event.comment
    
    # Broadcast chat ke frontend
    await manager.broadcast("chat", {"username": username, "comment": comment})
    
    # Cek logika tebak kata
    if game.guess(username, comment):
        await manager.broadcast("system", {"message": f"{username} berhasil menebak kata!"})
        await manager.broadcast_game_state()

# ==========================================
# BACKGROUND TASK (STANDBY MODE)
# ==========================================
async def start_tiktok_client():
    while True:
        try:
            await client.start()
        except Exception as e:
            # Standby mode jika offline/error, retry setiap 10 detik
            await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_tiktok_client())

# ==========================================
# FRONTEND STRINGS (HTML, CSS, JS, PWA)
# ==========================================
MANIFEST_JSON = """
{
  "name": "TikTok Live Game",
  "short_name": "TTGame",
  "start_url": "/",
  "display": "fullscreen",
  "background_color": "#0f172a",
  "theme_color": "#0f172a",
  "icons": [{
    "src": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI1MCIgZmlsbD0iIzM0OTg=","sizes": "192x192","type": "image/svg+xml"
  }]
}
"""

SERVICE_WORKER_JS = """
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open('ttgame-v1').then((cache) => cache.addAll(['/'])));
});
self.addEventListener('fetch', (e) => {
  e.respondWith(caches.match(e.request).then((response) => response || fetch(e.request)));
});
"""

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>TikTok Live Game - Tebak Kata</title>
    <link rel="manifest" href="/manifest.json">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #000; display: flex; justify-content: center; align-items: center; height: 100vh; color: #fff; overflow: hidden; }
        
        #app-container {
            width: 100%;
            max-width: 100vw;
            aspect-ratio: 4 / 3;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            position: relative;
            display: grid;
            grid-template-columns: 3fr 1fr;
            grid-template-rows: auto 1fr;
            box-shadow: 0 0 20px rgba(0,0,0,0.8);
        }

        /* HEADER / STATS */
        header { grid-column: 1 / 3; background: rgba(0,0,0,0.5); padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #334155; }
        .stats-group { display: flex; gap: 20px; }
        .stat-item { display: flex; align-items: center; gap: 8px; font-size: 1.1rem; font-weight: bold; }
        .stat-item i { color: #38bdf8; }
        
        /* FULLSCREEN BTN */
        #fs-btn { background: #38bdf8; color: #000; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        #fs-btn:hover { background: #0ea5e9; }

        /* GAME AREA */
        .game-area { display: flex; flex-direction: column; justify-content: center; align-items: center; border-right: 2px solid #334155; position: relative; }
        .scrambled-word { font-size: 4rem; letter-spacing: 15px; font-weight: 900; color: #fbbf24; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); margin-bottom: 20px; }
        .instruction { font-size: 1.5rem; color: #94a3b8; }

        /* NOTIFICATIONS */
        .log-container { position: absolute; bottom: 20px; left: 20px; right: 20px; height: 60px; overflow: hidden; }
        .log-item { background: rgba(56, 189, 248, 0.2); border-left: 4px solid #38bdf8; padding: 8px 15px; margin-bottom: 5px; border-radius: 4px; animation: fadeOut 4s forwards; }
        @keyframes fadeOut { 0% { opacity: 1; transform: translateY(0); } 80% { opacity: 1; } 100% { opacity: 0; transform: translateY(-10px); } }

        /* SIDEBAR (TOP USERS & CHAT) */
        .sidebar { display: flex; flex-direction: column; background: rgba(0,0,0,0.3); }
        .top-users { padding: 15px; border-bottom: 2px solid #334155; height: 35%; overflow: hidden; }
        .section-title { font-size: 1rem; color: #94a3b8; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .user-row { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 8px 10px; margin-bottom: 8px; border-radius: 5px; }
        .user-name { max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: bold; }
        .user-score { color: #fbbf24; font-weight: bold; }

        .chat-container { padding: 15px; flex-grow: 1; overflow-y: hidden; display: flex; flex-direction: column; }
        .chat-list { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; scrollbar-width: none; }
        .chat-list::-webkit-scrollbar { display: none; }
        .chat-msg { background: #0f172a; padding: 8px; border-radius: 5px; font-size: 0.95rem; line-height: 1.3; }
        .chat-author { color: #a3e635; font-weight: bold; }
    </style>
</head>
<body>

<div id="app-container">
    <header>
        <div class="stats-group">
            <div class="stat-item"><i class="fa-solid fa-eye"></i> <span id="val-viewers">0</span></div>
            <div class="stat-item"><i class="fa-solid fa-heart"></i> <span id="val-likes">0</span></div>
            <div class="stat-item"><i class="fa-solid fa-share"></i> <span id="val-shares">0</span></div>
        </div>
        <button id="fs-btn"><i class="fa-solid fa-expand"></i> Layar Penuh</button>
    </header>

    <main class="game-area">
        <div class="scrambled-word" id="word-display">MEMUAT</div>
        <div class="instruction">Tebak kata dari susunan huruf di atas!</div>
        <div class="log-container" id="log-list"></div>
    </main>

    <aside class="sidebar">
        <div class="top-users">
            <div class="section-title"><i class="fa-solid fa-trophy"></i> Top 3 Penebak</div>
            <div id="top-users-list">
                </div>
        </div>
        <div class="chat-container">
            <div class="section-title"><i class="fa-solid fa-comments"></i> Live Chat</div>
            <div class="chat-list" id="chat-list">
                </div>
        </div>
    </aside>
</div>

<script>
    // PWA Setup
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js');
    }

    // Fullscreen Logic
    const appContainer = document.getElementById('app-container');
    document.getElementById('fs-btn').addEventListener('click', () => {
        if (!document.fullscreenElement) {
            appContainer.requestFullscreen().catch(err => console.log(err));
        } else {
            document.exitFullscreen();
        }
    });

    // WebSocket Logic
    let ws;
    function connectWS() {
        ws = new WebSocket(`ws://${location.host}/ws`);
        
        ws.onmessage = (event) => {
            const res = JSON.parse(event.data);
            
            if (res.type === 'game_update') {
                document.getElementById('word-display').innerText = res.data.scrambled;
                updateStats(res.data.stats);
                updateTopUsers(res.data.top_users);
            } 
            else if (res.type === 'stats_update') {
                updateStats(res.data);
            }
            else if (res.type === 'chat') {
                addChat(res.data.username, res.data.comment);
            }
            else if (res.type === 'notification' || res.type === 'system') {
                addLog(res.data.message);
            }
        };

        ws.onclose = () => {
            setTimeout(connectWS, 3000); // Reconnect standby
        };
    }

    function updateStats(stats) {
        document.getElementById('val-viewers').innerText = stats.viewers;
        document.getElementById('val-likes').innerText = stats.likes;
        document.getElementById('val-shares').innerText = stats.shares;
    }

    function updateTopUsers(users) {
        const container = document.getElementById('top-users-list');
        container.innerHTML = '';
        users.forEach(u => {
            container.innerHTML += `
                <div class="user-row">
                    <span class="user-name">${u.username}</span>
                    <span class="user-score">${u.score} Pts</span>
                </div>
            `;
        });
    }

    function addChat(username, comment) {
        const list = document.getElementById('chat-list');
        const div = document.createElement('div');
        div.className = 'chat-msg';
        div.innerHTML = `<span class="chat-author">${username}:</span> <span class="chat-text">${comment}</span>`;
        list.appendChild(div);
        if (list.childElementCount > 30) list.removeChild(list.firstChild);
        list.scrollTop = list.scrollHeight;
    }

    function addLog(msg) {
        const list = document.getElementById('log-list');
        const div = document.createElement('div');
        div.className = 'log-item';
        div.innerHTML = `<i class="fa-solid fa-bell"></i> ${msg}`;
        list.appendChild(div);
        setTimeout(() => { if(div.parentNode) div.remove(); }, 4000);
    }

    connectWS();
</script>
</body>
</html>
"""

# ==========================================
# ENDPOINTS FASTAPI
# ==========================================
@app.get("/")
async def get_index():
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/manifest.json")
async def get_manifest():
    return Response(content=MANIFEST_JSON, media_type="application/json")

@app.get("/sw.js")
async def get_sw():
    return Response(content=SERVICE_WORKER_JS, media_type="application/javascript")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep-alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")