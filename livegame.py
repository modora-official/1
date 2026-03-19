import asyncio
import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
import uvicorn

app = FastAPI()
# Target username TikTok
client = TikTokLiveClient(unique_id="@c_poek")
connected_websockets = set()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Live Game - c_poek</title>
    <style>
        body { 
            margin: 0; padding: 0; background-color: #000; display: flex; 
            justify-content: center; align-items: center; height: 100vh; 
            overflow: hidden; color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        }
        /* Container Rasio 4:3 */
        #game-container { 
            width: 100vw; max-width: 133.33vh; height: 100vh; max-height: 75vw; 
            background: linear-gradient(135deg, #1e1e1e, #2a2a2a); position: relative; 
            aspect-ratio: 4 / 3; display: flex; flex-direction: column; 
            align-items: center; justify-content: center; box-sizing: border-box;
            box-shadow: 0 0 20px rgba(0,0,0,0.8);
        }
        #btn-fullscreen { 
            position: absolute; top: 20px; padding: 12px 24px; background: #ff0050; 
            color: white; border: none; border-radius: 8px; cursor: pointer; 
            z-index: 10; font-weight: bold; font-size: 1.2rem;
        }
        .player-bar { position: absolute; bottom: 15%; width: 80px; transition: height 0.3s ease-out; border-radius: 10px 10px 0 0; }
        #player-kiri { left: 15%; background: linear-gradient(to top, #0052D4, #4364F7); height: 50%; }
        #player-kanan { right: 15%; background: linear-gradient(to top, #cb2d3e, #ef473a); height: 50%; }
        .score { position: absolute; top: 15%; font-size: 4rem; font-weight: 900; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
        #score-kiri { left: 15%; color: #4364F7; }
        #score-kanan { right: 15%; color: #ef473a; }
        .instruction { position: absolute; bottom: 5%; font-size: 1.8rem; text-align: center; width: 100%; font-weight: bold; }
        .instruction span { color: #ff0050; }
    </style>
</head>
<body>
    <div id="game-container">
        <button id="btn-fullscreen" onclick="masukFullscreen()">Mulai Fullscreen 4:3</button>
        <div id="score-kiri" class="score">50</div>
        <div id="score-kanan" class="score">50</div>
        <div id="player-kiri" class="player-bar"></div>
        <div id="player-kanan" class="player-bar"></div>
        <div class="instruction">Ketik <span>KIRI</span> atau <span>KANAN</span> di Komentar!</div>
    </div>
    <script>
        let scoreKiri = 50;
        let scoreKanan = 50;
        
        // Koneksi WebSockets ke Termux Backend
        const ws = new WebSocket(`ws://${location.host}/ws`);

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const comment = data.comment.toUpperCase().trim();
            
            if (comment === 'KIRI') {
                scoreKiri += 2; scoreKanan -= 2;
            } else if (comment === 'KANAN') {
                scoreKanan += 2; scoreKiri -= 2;
            }
            updateUI();
        };

        function updateUI() {
            if(scoreKiri > 100) { scoreKiri = 100; scoreKanan = 0; }
            if(scoreKanan > 100) { scoreKanan = 100; scoreKiri = 0; }

            document.getElementById('score-kiri').innerText = scoreKiri;
            document.getElementById('score-kanan').innerText = scoreKanan;
            document.getElementById('player-kiri').style.height = scoreKiri + '%';
            document.getElementById('player-kanan').style.height = scoreKanan + '%';
        }

        // Fungsi menghilangkan bar sinyal dan masuk mode profesional
        function masukFullscreen() {
            const elem = document.documentElement;
            if (elem.requestFullscreen) { elem.requestFullscreen(); }
            else if (elem.webkitRequestFullscreen) { elem.webkitRequestFullscreen(); }
            
            // Putar layar ke landscape jika didukung browser
            if (screen.orientation && screen.orientation.lock) {
                screen.orientation.lock('landscape').catch(function(error) { console.log("Orientation lock failed"); });
            }
            document.getElementById('btn-fullscreen').style.display = 'none';
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
        await client.start()
    except Exception as e:
        print(f"Gagal konek ke TikTok: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_tiktok())

if __name__ == "__main__":
    print("Server Game Berjalan! Buka http://127.0.0.1:8000 di Google Chrome HP Anda.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
