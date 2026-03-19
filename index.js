const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const { WebcastPushConnection } = require('tiktok-live-connector');

const tiktokUsername = "c_poek";
let flagScores = {};
let gameActive = true;

const gameUI = `
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <title>Live Game - c_poek</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,800;1,900&display=swap" rel="stylesheet">
    <style>
        body { margin: 0; background: #0b0c10; color: #c5c6c7; font-family: 'Poppins', sans-serif; overflow: hidden; display: flex; justify-content: center; align-items: center; height: 100vh; touch-action: none; }
        /* Rasio fix 4:3 Landscape */
        #game-container {
            width: 100vw; height: 100vh;
            max-width: calc(100vh * (4/3)); max-height: calc(100vw * (3/4));
            aspect-ratio: 4/3;
            background: radial-gradient(circle, #1f2833 0%, #0b0c10 100%);
            position: relative; border: 4px solid #66fcf1; box-shadow: 0 0 30px #66fcf1;
            display: flex; flex-direction: column; padding: 15px; box-sizing: border-box;
        }
        .title { text-align: center; color: #45a29e; text-shadow: 0 0 10px #45a29e; font-size: 3vh; margin: 0 0 15px 0; text-transform: uppercase; letter-spacing: 3px; z-index: 10; }
        .tap-hint { position: absolute; top: 10px; right: 15px; font-size: 1.5vh; color: #fff; opacity: 0.5; z-index: 50; }
        
        .tracks { flex: 1; display: flex; flex-direction: column; justify-content: space-around; position: relative; }
        .finish-line { position: absolute; right: 2%; top: 0; bottom: 0; width: 12px; background: repeating-linear-gradient(45deg, #fff, #fff 10px, #000 10px, #000 20px); border: 2px solid #fff; z-index: 0; box-shadow: 0 0 15px rgba(255,255,255,0.5); }
        
        .track { display: flex; align-items: center; background: rgba(0,0,0,0.6); border-radius: 50px; height: 13%; padding: 0 15px; border: 2px solid #45a29e; position: relative; z-index: 1; }
        .bar { height: 100%; position: absolute; left: 0; top: 0; background: linear-gradient(90deg, #45a29e, #66fcf1); border-radius: 50px; transition: width 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); box-shadow: inset 0 0 10px rgba(255,255,255,0.5), 0 0 15px #66fcf1; }
        .flag { font-size: 4.5vh; z-index: 2; margin-right: 15px; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.8)); }
        .percent { z-index: 2; margin-left: auto; font-size: 3.5vh; font-weight: 900; color: #fff; text-shadow: 2px 2px 0 #000; }
        
        #winner-screen { position: absolute; inset: 0; background: rgba(0,0,0,0.95); z-index: 100; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
        #winner-screen h1 { color: #66fcf1; font-size: 8vh; text-shadow: 0 0 30px #66fcf1; margin: 0; animation: pulse 1s infinite; }
        #winner-flag { font-size: 12vh; margin-top: 20px; filter: drop-shadow(0 0 20px rgba(255,255,255,0.5)); }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
    </style>
</head>
<body onclick="goFullscreen()">
    <div id="game-container">
        <div class="tap-hint">Tap layar untuk Fullscreen</div>
        <h1 class="title">🏁 World Flag Race 🏁</h1>
        <div class="tracks" id="track-container">
            <div class="finish-line"></div>
            </div>
        <div id="winner-screen">
            <h1>WINNER!</h1>
            <div id="winner-flag">🇮🇩</div>
        </div>
    </div>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        const socket = io();
        const container = document.getElementById('track-container');
        const winnerScreen = document.getElementById('winner-screen');
        const winnerFlag = document.getElementById('winner-flag');

        // Bikin layar benar-benar full screen tanpa status bar
        function goFullscreen() {
            let elem = document.documentElement;
            if (elem.requestFullscreen) { elem.requestFullscreen(); }
            else if (elem.webkitRequestFullscreen) { elem.webkitRequestFullscreen(); }
            document.querySelector('.tap-hint').style.display = 'none';
        }

        socket.on('update', (data) => {
            // Ambil top 6
            const topFlags = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 6);
            
            // Render ulang HTML dengan animasi yang smooth
            let html = '<div class="finish-line"></div>';
            topFlags.forEach(([flag, score]) => {
                const displayScore = Math.min(score, 100);
                html += \`
                    <div class="track">
                        <div class="bar" style="width: \${displayScore}%"></div>
                        <div class="flag">\${flag}</div>
                        <div class="percent">\${displayScore}%</div>
                    </div>
                \`;
            });
            container.innerHTML = html;
        });

        socket.on('winner', (flag) => {
            winnerFlag.innerText = flag;
            winnerScreen.style.display = 'flex';
        });

        socket.on('reset', () => {
            winnerScreen.style.display = 'none';
            container.innerHTML = '<div class="finish-line"></div>';
        });
    </script>
</body>
</html>
`;

app.get('/', (req, res) => res.send(gameUI));

const tiktokLiveConnection = new WebcastPushConnection(tiktokUsername);
tiktokLiveConnection.connect()
    .then(state => console.log(\`✅ Live Terhubung: \${tiktokUsername} | Room ID: \${state.roomId}\`))
    .catch(err => console.error('❌ Gagal Konek:', err));

tiktokLiveConnection.on('chat', data => {
    if(!gameActive) return;
    
    // Deteksi emoji bendera
    const flags = data.comment.match(/[\uD83C][\uDDE6-\uDDFF][\uD83C][\uDDE6-\uDDFF]/g);
    if (flags) {
        let winnerFound = null;
        flags.forEach(flag => {
            flagScores[flag] = (flagScores[flag] || 0) + 3; // Tambah 3% per komen
            if(flagScores[flag] >= 100) winnerFound = flag;
        });
        
        io.emit('update', flagScores);

        // Sistem Auto-Reset Profesional kalau ada yang 100%
        if(winnerFound) {
            gameActive = false;
            io.emit('winner', winnerFound);
            console.log(\`🎉 Pemenang: \${winnerFound}!\`);
            
            setTimeout(() => {
                flagScores = {};
                gameActive = true;
                io.emit('reset');
                console.log('🔄 Game di-reset otomatis.');
            }, 6000); // Reset setelah 6 detik
        }
    }
});

http.listen(3000, () => console.log('🚀 Server ON -> http://localhost:3000'));
