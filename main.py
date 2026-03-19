import threading
import asyncio
from flask import Flask, jsonify, request
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, LikeEvent, JoinEvent, ShareEvent, ViewerCountUpdateEvent

# Konfigurasi
TIKTOK_USERNAME = "c_poek"
PORT = 5000

app = Flask(__name__)
client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

# State Management
event_queue = []
dashboard_state = {
    "viewers": 0,
    "likes": 0,
    "joined": 0,
    "shares": 0,
    "comments": 0,
    "status": "Menunggu Live..."
}

# --- TikTokLive Events ---
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    dashboard_state["status"] = f"Terhubung: {event.room_id}"

@client.on(ViewerCountUpdateEvent)
async def on_viewer_count(event: ViewerCountUpdateEvent):
    dashboard_state["viewers"] = event.viewer_count

@client.on(LikeEvent)
async def on_like(event: LikeEvent):
    dashboard_state["likes"] += event.like_count

@client.on(JoinEvent)
async def on_join(event: JoinEvent):
    dashboard_state["joined"] += 1

@client.on(ShareEvent)
async def on_share(event: ShareEvent):
    dashboard_state["shares"] += 1

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    dashboard_state["comments"] += 1
    event_queue.append({
        "type": "comment",
        "user": event.user.nickname,
        "text": event.comment
    })

def start_tiktok_client():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(client.start())
    except Exception as e:
        print(f"Error TikTokLive: {e}")

# --- Web & PWA Routes ---
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Game PWA</title>
    <link rel="manifest" href="/manifest.json">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: #0f172a; display: flex; justify-content: center; align-items: center; height: 100vh; width: 100vw; font-family: 'Segoe UI', sans-serif; color: #f8fafc; overflow: hidden; }
        #app-container { aspect-ratio: 4 / 3; width: 100%; max-height: 100vh; max-width: calc(100vh * (4/3)); background: #1e293b; box-shadow: 0 0 20px rgba(0,0,0,0.8); display: flex; flex-direction: column; overflow: hidden; position: relative; }
        
        /* Header / Dashboard */
        .dashboard { display: grid; grid-template-columns: repeat(6, 1fr); background: #0f172a; padding: 10px; border-bottom: 2px solid #334155; text-align: center; font-size: 14px; font-weight: bold; }
        .stat-box { display: flex; flex-direction: column; align-items: center; justify-content: center; border-right: 1px solid #334155; }
        .stat-box:last-child { border-right: none; }
        .stat-box i { font-size: 18px; margin-bottom: 5px; color: #38bdf8; }
        .stat-box span { color: #94a3b8; font-size: 12px; }

        /* Main Game Area */
        .game-area { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }
        .word-display { font-size: 50px; letter-spacing: 15px; font-weight: bold; color: #fbbf24; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); margin-bottom: 20px; }
        .question-text { font-size: 20px; color: #94a3b8; margin-bottom: 30px; }
        .status-bar { position: absolute; bottom: 10px; left: 10px; font-size: 12px; color: #22c55e; }

        /* Leaderboard */
        .leaderboard { position: absolute; top: 10px; right: 10px; background: rgba(15, 23, 42, 0.8); padding: 10px; border-radius: 8px; width: 220px; border: 1px solid #334155; }
        .leaderboard h3 { font-size: 14px; text-transform: uppercase; border-bottom: 1px solid #334155; padding-bottom: 5px; margin-bottom: 5px; text-align: center; color: #f43f5e; }
        .top-user { display: flex; justify-content: space-between; font-size: 14px; margin: 5px 0; }
        .username { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px; }
        .score { font-weight: bold; color: #fbbf24; }
    </style>
</head>
<body>
    <div id="app-container">
        <div class="dashboard">
            <div class="stat-box"><i class="fas fa-eye"></i><div id="val-viewers">0</div><span>Penonton</span></div>
            <div class="stat-box"><i class="fas fa-user-plus"></i><div id="val-joined">0</div><span>Bergabung</span></div>
            <div class="stat-box"><i class="fas fa-heart"></i><div id="val-likes">0</div><span>Likes</span></div>
            <div class="stat-box"><i class="fas fa-comment"></i><div id="val-comments">0</div><span>Komentar</span></div>
            <div class="stat-box"><i class="fas fa-share"></i><div id="val-shares">0</div><span>Share</span></div>
            <div class="stat-box"><i class="fas fa-signal"></i><div id="val-status">Standby</div><span>Status</span></div>
        </div>

        <div class="game-area">
            <div class="leaderboard">
                <h3><i class="fas fa-trophy"></i> Top 3 Users</h3>
                <div id="lb-content"></div>
            </div>
            
            <div class="question-text"><i class="fas fa-gamepad"></i> Tebak Kata di Komentar!</div>
            <div class="word-display" id="word-display">_ _ _ _ _</div>
            <div class="status-bar"><i class="fas fa-circle-check"></i> Real-time Active</div>
        </div>
    </div>

    <script>
        // Registrasi Service Worker untuk PWA
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(err => console.error(err));
        }

        const databaseKata = ["GITHUB", "TERMUX", "WEBSITE", "PROGRAMMER", "INTERNET", "KOMPUTER", "APLIKASI", "SERVER"];
        let kataRahasia = "";
        let kataTebakan = [];
        let skorUser = {};

        function pilihKataBaru() {
            kataRahasia = databaseKata[Math.floor(Math.random() * databaseKata.length)];
            let arrayTebakan = [];
            for (let i = 0; i < kataRahasia.length; i++) {
                // Tampilkan huruf pertama, terakhir, atau acak. Sisanya underscore
                if (i === 0 || i === kataRahasia.length - 1 || Math.random() > 0.6) {
                    arrayTebakan.push(kataRahasia[i]);
                } else {
                    arrayTebakan.push("_");
                }
            }
            if (!arrayTebakan.includes("_")) arrayTebakan[1] = "_"; // Wajib ada huruf hilang
            kataTebakan = arrayTebakan;
            document.getElementById('word-display').innerText = kataTebakan.join(" ");
        }

        function updateLeaderboard() {
            const sortedUsers = Object.entries(skorUser).sort((a, b) => b[1] - a[1]).slice(0, 3);
            let html = "";
            sortedUsers.forEach((user, index) => {
                let medal = index === 0 ? '<i class="fas fa-medal" style="color:gold"></i> ' : 
                            index === 1 ? '<i class="fas fa-medal" style="color:silver"></i> ' : 
                                          '<i class="fas fa-medal" style="color:#cd7f32"></i> ';
                html += `<div class="top-user">${medal}<span class="username">${user[0]}</span> <span class="score">${user[1]}</span></div>`;
            });
            document.getElementById('lb-content').innerHTML = html;
        }

        async function fetchEvents() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                // Update Dashboard
                document.getElementById('val-viewers').innerText = data.state.viewers;
                document.getElementById('val-joined').innerText = data.state.joined;
                document.getElementById('val-likes').innerText = data.state.likes;
                document.getElementById('val-comments').innerText = data.state.comments;
                document.getElementById('val-shares').innerText = data.state.shares;
                document.getElementById('val-status').innerText = "Live";
                
                // Cek Jawaban dari Komentar
                data.events.forEach(ev => {
                    if (ev.type === "comment") {
                        if (ev.text.toUpperCase() === kataRahasia.toUpperCase()) {
                            if (!skorUser[ev.user]) skorUser[ev.user] = 0;
                            skorUser[ev.user] += 10;
                            updateLeaderboard();
                            pilihKataBaru();
                        }
                    }
                });
            } catch (e) {
                console.log("Koneksi polling terputus, mencoba lagi...");
            }
        }

        pilihKataBaru();
        setInterval(fetchEvents, 1000); // Polling setiap detik (Real-time standby)
    </script>
</body>
</html>"""

@app.route('/api/data')
def api_data():
    global event_queue
    data_to_send = list(event_queue)
    event_queue.clear()
    return jsonify({
        "state": dashboard_state,
        "events": data_to_send
    })

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "Live Interactive Game",
        "short_name": "LiveGame",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#1e293b",
        "icons": [{
            "src": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/svgs/solid/gamepad.svg",
            "sizes": "192x192",
            "type": "image/svg+xml"
        }]
    }
    return jsonify(manifest_data)

@app.route('/sw.js')
def service_worker():
    return """
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', (e) => { e.respondWith(fetch(e.request)); });
""", 200, {'Content-Type': 'application/javascript'}

if __name__ == '__main__':
    # Jalankan TikTok Listener di Background Thread
    threading.Thread(target=start_tiktok_client, daemon=True).start()
    # Jalankan Web Server
    app.run(host='0.0.0.0', port=PORT, debug=False)