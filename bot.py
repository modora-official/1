from pyrogram import Client, filters
import ftplib
import os
import time
import asyncio

# ================= KREDENSIAL BOT & API =================
API_ID = 28529912
API_HASH = "c0189bbf4fe519babcdcc69d3c1230cb"
BOT_TOKEN = "8586628406:AAHvCTHTz1erJTiB_9RrxVcrEawWcqmfc_k"

# ================= KONFIGURASI HOSTING =================
FTP_HOST = "denali.iixcp.rumahweb.net"
FTP_USER = "modorazo"
FTP_PASS = "@Anjir!999" 
FTP_DIR = "public_html/RNDM" 
DOMAIN = "https://modorazone.it.com/RNDM"

app = Client("upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Fungsi persentase untuk Download dari Telegram
async def down_progress(current, total, msg, start_time):
    now = time.time()
    # Update pesan tiap 2 detik biar aman dari limit API Telegram
    if now - start_time[0] > 2:
        start_time[0] = now
        percent = (current / total) * 100
        try:
            await msg.edit_text(f"⏳ Mendownload dari Telegram: {percent:.1f}%")
        except Exception:
            pass

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Bot aktif!\n\nKirim file langsung untuk pakai nama asli, atau **tambahkan teks (caption)** pada file saat dikirim untuk ganti nama file.")

@app.on_message(filters.document | filters.photo | filters.video | filters.audio)
async def handle_file(client, message):
    msg = await message.reply_text("⏳ Memulai proses...")
    
    try:
        # ================= 1. PROSES DOWNLOAD =================
        start_time = [time.time()]
        file_path = await message.download(progress=down_progress, progress_args=(msg, start_time))
        
        if not file_path:
            await msg.edit_text("❌ Gagal mendownload file dari server Telegram.")
            return

        # ================= 2. NAMA FILE OPSIONAL =================
        original_ext = os.path.splitext(file_path)[1]
        
        if message.caption:
            # Ambil dari caption dan ganti spasi jadi underscore biar link gak rusak
            file_name = message.caption.replace(" ", "_")
            # Kalau user gak nulis ekstensi (misal ".apk"), tambahin otomatis dari aslinya
            if not os.path.splitext(file_name)[1]:
                file_name += original_ext
        else:
            file_name = os.path.basename(file_path)

        await msg.edit_text(f"✅ Download 100%. Menyiapkan upload ke cPanel...\n📂 Nama file: {file_name}")
        
        # ================= 3. PROSES UPLOAD FTP =================
        total_size = os.path.getsize(file_path)
        uploaded_bytes = 0
        last_update = time.time()
        loop = asyncio.get_event_loop()

        # Fungsi aman untuk ngedit pesan dari dalam thread FTP
        async def safe_edit(text):
            try:
                await msg.edit_text(text)
            except Exception:
                pass

        # Fungsi persentase untuk Upload ke FTP
        def ftp_callback(block):
            nonlocal uploaded_bytes, last_update
            uploaded_bytes += len(block)
            now = time.time()
            if now - last_update > 2 or uploaded_bytes == total_size:
                last_update = now
                percent = (uploaded_bytes / total_size) * 100
                asyncio.run_coroutine_threadsafe(
                    safe_edit(f"☁️ Mengupload ke cPanel: {percent:.1f}%"), 
                    loop
                )

        def ftp_upload_task():
            ftp = ftplib.FTP(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            
            dirs = FTP_DIR.split('/')
            for d in dirs:
                if d:
                    try:
                        ftp.cwd(d)
                    except ftplib.error_perm:
                        ftp.mkd(d)
                        ftp.cwd(d)

            with open(file_path, "rb") as file:
                ftp.storbinary(f"STOR {file_name}", file, callback=ftp_callback)
            ftp.quit()

        # Jalankan FTP pakai background thread biar bot gak nge-freeze
        await asyncio.to_thread(ftp_upload_task)

        # Hapus file lokal di HP/Termux biar memori lega
        os.remove(file_path)

        file_url = f"{DOMAIN}/{file_name}"
        await msg.edit_text(f"✅ **Sukses Upload!**\n\n🔗 Link: {file_url}")
            
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

print("Bot Pyrogram aktif dengan fitur Real-Time Progress & Custom Name!")
app.run()
