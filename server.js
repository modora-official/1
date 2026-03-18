const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const { WebcastPushConnection } = require('tiktok-live-connector');

// ==========================================
// 1. DATA PWA (Biar jadi Aplikasi)
// ==========================================
const manifestJson = {
    "name": "Live Flag Race", "short_name": "FlagRace", "start_url": "/", "display": "fullscreen",
    "orientation": "landscape", "background_color": "#09090b", "theme_color": "#3b82f6",
    "icons": [{"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}]
};
app.get('/manifest.json', (req, res) => res.json(manifestJson));
app.get('/icon.svg', (req, res) => { res.setHeader('Content-Type', 'image/svg+xml'); res.send(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#3b82f6"/><text x="50%" y="50%" font-size="40" text-anchor="middle" dy=".3em" fill="#fff">🏁</text></svg>`); });

// ==========================================
// 2. TAMPILAN UI/UX PRO (Frontend)
// ==========================================
const htmlPage = `
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Live Bar Race Pro</title>
    <link rel="manifest" href="/manifest.json">
    <style>
        :root { --bg: #09090b; --panel: #18181b; --text: #f8fafc; --accent: #3b82f6; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background-color: var(--bg); color: var(--text); overflow: hidden; height: 100vh; width: 100vw; }
        
        /* OVERLAY SETUP (Biar Fullscreen & Input Username) */
        #setup-screen { position: absolute; inset: 0; background: rgba(0,0,0,0.9); z-index: 999; display: flex; flex-direction: column; align-items: center; justify-content: center; backdrop-filter: blur(10px); }
        .setup-box { background: var(--panel); padding: 30px; border-radius: 15px; text-align: center; border: 1px solid #333; box-shadow: 0 0 20px rgba(59,130,246,0.3); }
        .setup-box h2 { margin-bottom: 20px; color: #fff; }
        input { padding: 12px 20px; font-size: 16px; border-radius: 8px; border: 1px solid #444; background: #222; color: #fff; width: 100%; margin-bottom: 15px; outline: none; text-align: center; }
        button { background: linear-gradient(90deg, #3b82f6, #2563eb); color: white; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; transition: 0.2s; text-transform: uppercase; letter-spacing: 1px; }
        button:hover { transform: scale(1.05); box-shadow: 0 0 15px #3b82f6; }
        
        /* AREA GAME UTAMA */
        #game-screen { display: none; flex-direction: column; height: 100%; padding: 15px; padding-right: 280px; position: relative; }
        header { text-align: center; margin-bottom: 15px; }
        h1 { font-size: 26px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px var(--accent); }
        .status { font-size: 14px; font-weight: bold; color: #ef4444; margin-top: 5px; text-shadow: 0 0 5px red; }
        .status.online { color: #22c55e; text-shadow: 0 0 5px #22c55e; }

        /* LEADERBOARD & BENDERA */
        .leaderboard { display: flex; flex-direction: column; gap: 10px; flex: 1; justify-content: center; }
        .row { display: flex; align-items: center; background: rgba(24, 24, 27, 0.8); padding: 8px 15px; border-radius: 12px; border: 1px solid #333; }
        .flag { font-size: 35px; min-width: 50px; text-align: center; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.6)); transition: transform 0.2s; }
        .flag.bounce { transform: scale(1.3) translateY(-5px); }
        
        .track-container { flex: 1; margin: 0 15px; background: #000; border-radius: 20px; height: 26px; overflow: hidden; border: 1px solid #222; }
        .bar { height: 100%; width: 3%; border-radius: 20px; transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; }
        .bar::after { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent); animation: shimmer 1.5s infinite linear; }
        .score { font-size: 20px; font-weight: 900; min-width: 45px; text-align: right; color: #fff; text-shadow: 1px 1px 3px #000; }
        
        /* NOTIFIKASI REALTIME */
        .notif-container { position: absolute; top: 15px; right: 15px; width: 250px; display: flex; flex-direction: column; gap: 8px; z-index: 50; }
        .notif { background: rgba(24, 24, 27, 0.9); border-left: 4px solid #3b82f6; padding: 10px 15px; border-radius: 8px; color: white; font-size: 13px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.5); border-top: 1px solid #333; border-right: 1px solid #333; border-bottom: 1px solid #333; animation: slideIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        
        @keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
        @keyframes slideIn { from { transform: translateX(120%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes slideOut { to { transform: translateX(120%); opacity: 0; } }
    </style>
</head>
<body>

    <div id="setup-screen">
        <div class="setup-box">
            <h2>PENGATURAN LIVE</h2>
            <input type="text" id="usernameInput" placeholder="Masukkan Username TikTok..." value="gamemodapkofficial">
            <button onclick="startGame()">Mulai & Layar Penuh</button>
        </div>
    </div>

    <div id="game-screen">
        <header>
            <h1>🏆 FLAG WAR RACE 🏆</h1>
            <div class="status" id="conn-status">🔴 Menunggu Koneksi...</div>
        </header>

        <div class="leaderboard" id="board"></div>
        <div class="notif-container" id="notif-area"></div>
    </div>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        const socket = io();
        const board = document.getElementById('board');
        const statusEl = document.getElementById('conn-status');
        const notifArea = document.getElementById('notif-area');

        // FUNGSI LAYAR PENUH & LANDSCAPE
        function startGame() {
            let user = document.getElementById('usernameInput').value.trim();
            if(!user) return alert("Username nggak boleh kosong!");
            
            let elem = document.documentElement;
            if (elem.requestFullscreen) { elem.requestFullscreen().catch(e => console.log(e)); }
            
            // Kunci ke Landscape
            if(screen.orientation && screen.orientation.lock) {
                screen.orientation.lock('landscape').catch(e => console.log(e));
            }

            document.getElementById('setup-screen').style.display = 'none';
            document.getElementById('game-screen').style.display = 'flex';
            
            statusEl.innerHTML = '🔄 Menghubungkan ke @' + user + '...';
            socket.emit('connectToTiktok', user);
        }

        // FUNGSI NOTIFIKASI
        socket.on('notify', (data) => {
            const el = document.createElement('div');
            el.className = 'notif';
            el.innerHTML = data.msg;
            if(data.color) el.style.borderLeftColor = data.color;
            notifArea.appendChild(el);
            
            // Hapus notif setelah 4 detik
            setTimeout(() => {
                el.style.animation = 'slideOut 0.3s forwards';
                setTimeout(() => el.remove(), 300);
            }, 4000);
        });

        // STATUS KONEKSI
        socket.on('status', (data) => {
            if(data.type === 'online') {
                statusEl.className = 'status online';
                statusEl.innerHTML = '🟢 LIVE TERHUBUNG!';
            } else {
                statusEl.className = 'status';
                statusEl.innerHTML = '🔴 ' + data.msg;
            }
        });

        // UPDATE BENDERA
        let prevScores = {};
        socket.on('updateData', (topFlags) => {
            board.innerHTML = ''; 
            
            topFlags.forEach((item, index) => {
                let percentage = Math.max(3, Math.min(100, item.score)); 
                let barColor = index === 0 ? 'linear-gradient(90deg, #eab308, #fef08a)' : 
                               index === 1 ? 'linear-gradient(90deg, #94a3b8, #e2e8f0)' : 
                               index === 2 ? 'linear-gradient(90deg, #b45309, #fcd34d)' : 
                               'linear-gradient(90deg, #3b82f6, #60a5fa)';

                // Efek mantul kalau skor nambah
                let isBounce = prevScores[item.flag] && prevScores[item.flag] < item.score ? 'bounce' : '';
                prevScores[item.flag] = item.score;

                const row = document.createElement('div');
                row.className = 'row';
                row.innerHTML = \`
                    <div class="flag \${isBounce}">\${item.flag}</div>
                    <div class="track-container">
                        <div class="bar" style="width: \${percentage}%; background: \${barColor}"></div>
                    </div>
                    <div class="score">\${item.score}</div>
                \`;
                board.appendChild(row);
            });
        });
    </script>
</body>
</html>
`;

app.get('/', (req, res) => { res.send(htmlPage); });

// ==========================================
// 3. MESIN BACKEND & KONEKSI TIKTOK
// ==========================================
let activeConnection = null;
let flagScores = {};
const MAX_SCORE = 100;
const flagRegex = /(?:\uD83C[\uDDE6-\uDDFF]){2}/g;

function getTop6() {
    return Object.keys(flagScores)
        .map(flag => ({ flag, score: flagScores[flag] }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 6);
}

io.on('connection', (socket) => {
    
    // KONEKSI DIMULAI SAAT TOMBOL DI WEB DITEKAN
    socket.on('connectToTiktok', (username) => {
        if(activeConnection) { activeConnection.disconnect(); }
        
        console.log(\`\n🔄 Nyoba konek ke: \${username}\`);
        activeConnection = new WebcastPushConnection(username, { enableExtendedGiftInfo: true });

        activeConnection.connect().then(state => {
            console.info(\`✅ BERHASIL KONEK KE LIVE: \${state.roomInfo.owner.display_id}\`);
            socket.emit('status', { type: 'online' });
            socket.emit('notify', { msg: '🎉 Berhasil terhubung ke Live!', color: '#22c55e' });
        }).catch(err => {
            console.error('❌ Gagal konek:', err.message);
            socket.emit('status', { type: 'error', msg: 'Gagal Konek. Pastikan udah mulai Live!' });
            socket.emit('notify', { msg: '❌ Gagal. Cek setting umur Live lu!', color: '#ef4444' });
        });

        // TANGKAP KOMENTAR BENDERA
        activeConnection.on('chat', data => {
            let detectedFlags = data.comment.match(flagRegex);
            if (detectedFlags) {
                let isUpdated = false;
                detectedFlags.forEach(flag => {
                    flagScores[flag] = (flagScores[flag] || 0) + 1;
                    isUpdated = true;
                    if(flagScores[flag] >= MAX_SCORE) {
                        setTimeout(() => { flagScores = {}; io.emit('updateData', []); }, 3000);
                    }
                });
                if(isUpdated) io.emit('updateData', getTop6());
            }
        });

        // TANGKAP EVENT UNTUK NOTIFIKASI
        activeConnection.on('gift', data => {
            socket.emit('notify', { msg: \`🎁 <b>\${data.uniqueId}</b> ngirim <b>\${data.giftName}</b>!\`, color: '#eab308' });
        });
        
        activeConnection.on('like', data => {
            socket.emit('notify', { msg: \`❤️ <b>\${data.uniqueId}</b> tap-tap layar!\`, color: '#ef4444' });
        });

        activeConnection.on('follow', data => {
            socket.emit('notify', { msg: \`👤 <b>\${data.uniqueId}</b> mulai mengikuti!\`, color: '#3b82f6' });
        });

        activeConnection.on('member', data => {
            socket.emit('notify', { msg: \`👋 <b>\${data.uniqueId}</b> bergabung!\`, color: '#14b8a6' });
        });

        activeConnection.on('streamEnd', () => {
            socket.emit('status', { type: 'error', msg: 'Live Berakhir' });
        });
    });
});

http.listen(3000, () => {
    console.log('\n=======================================');
    console.log('🚀 SERVER JALAN BOSKU!');
    console.log('👉 Buka Chrome/Safari, ketik: http://localhost:3000');
    console.log('=======================================\n');
});
