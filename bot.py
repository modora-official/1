from pyrogram import Client, filters
import ftplib
import os
import time
import asyncio
import random
import string

# ================= KREDENSIAL BOT & API =================
API_ID = 28529912
API_HASH = "c0189bbf4fe519babcdcc69d3c1230cb"
BOT_TOKEN = "8681433472:AAFEegcen0BAvo7KIkA9eBSJ-EkJyjXoDtw"

# ================= KONFIGURASI HOSTING =================
FTP_HOST = "denali.iixcp.rumahweb.net"
FTP_USER = "modorazo"
FTP_PASS = "@Anjir!999" 
FTP_DIR = "public_html/RNDM" 
DOMAIN = "https://modorazone.it.com/RNDM"

app = Client("upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Fungsi pembuat nama acak: Huruf Awal Kapital + Acak + (Modora)
def get_random_filename(ext):
    # 1 huruf kapital di awal
    first_char = random.choice(string.ascii_uppercase)
    # 8 karakter acak (huruf kecil dan angka)
    rest_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # Gabungkan semuanya sesuai format
    return f"{first_char}{rest_chars} (Modora){ext}"

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("🚀 **Bot Upload Super Cepat Aktif!**\n\nKirimkan satu atau beberapa file sekaligus. Bot akan otomatis mengacak nama file dengan format `Random (Modora)` dan menguploadnya ke cPanel tanpa batasan kecepatan.")

# Nangkep semua jenis file yang dikirim (bisa multiple files sekaligus)
@app.on_message(filters.document | filters.photo | filters.video | filters.audio)
async def handle_file(client, message):
    status_msg = await message.reply_text("⏳ Memulai proses...")
    
    try:
        # ================= 1. DETEKSI EKSTENSI ASLI =================
        ext = ".bin" # Default fallback
        if message.document and message.document.file_name:
            ext = os.path.splitext(message.document.file_name)[1]
        elif message.photo:
            ext = ".jpg"
        elif message.video:
            if message.video.file_name:
                ext = os.path.splitext(message.video.file_name)[1]
            else:
                ext = ".mp4"
        elif message.audio:
            if message.audio.file_name:
                ext = os.path.splitext(message.audio.file_name)[1]
            else:
                ext = ".mp3"
                
        # Generate random name dengan format baru
        file_name = get_random_filename(ext)
        
        # ================= 2. PROSES DOWNLOAD (UNLIMITED SPEED) =================
        start_dl_time = time.time()
        last_dl_update = [time.time()]

        async def down_progress(current, total):
            now = time.time()
            # Update bar tiap 2 detik biar gak limit Telegram, tapi speed asli tetap ngebut
            if now - last_dl_update[0] > 2 or current == total:
                last_dl_update[0] = now
                elapsed = now - start_dl_time
                speed_bps = current / elapsed if elapsed > 0 else 0
                speed_mbps = speed_bps / (1024 * 1024)
                
                percent = (current / total) * 100 if total > 0 else 0
                curr_mb = current / (1024 * 1024)
                tot_mb = total / (1024 * 1024)
                
                text = f"📥 **Mendownload dari Telegram...**\n" \
                       f"📊 Progress: {percent:.1f}% ({curr_mb:.1f} MB / {tot_mb:.1f} MB)\n" \
                       f"🚀 Speed: {speed_mbps:.2f} MB/s"
                try: await status_msg.edit_text(text)
                except Exception: pass

        file_path = await message.download(progress=down_progress)
        
        if not file_path:
            await status_msg.edit_text("❌ Gagal mendownload file dari Telegram.")
            return
        
        # ================= 3. PROSES UPLOAD FTP (UNLIMITED SPEED) =================
        total_size = os.path.getsize(file_path)
        uploaded_bytes = 0
        start_up_time = time.time()
        last_up_update = time.time()
        loop = asyncio.get_event_loop()

        async def safe_edit(text):
            try: await status_msg.edit_text(text)
            except Exception: pass

        def ftp_callback(block):
            nonlocal uploaded_bytes, last_up_update
            uploaded_bytes += len(block)
            now = time.time()
            if now - last_up_update > 2 or uploaded_bytes == total_size:
                last_up_update = now
                elapsed = now - start_up_time
                speed_bps = uploaded_bytes / elapsed if elapsed > 0 else 0
                speed_mbps = speed_bps / (1024 * 1024)
                
                percent = (uploaded_bytes / total_size) * 100
                curr_mb = uploaded_bytes / (1024 * 1024)
                tot_mb = total_size / (1024 * 1024)
                
                text = f"☁️ **Mengupload ke cPanel...**\n" \
                       f"📊 Progress: {percent:.1f}% ({curr_mb:.1f} MB / {tot_mb:.1f} MB)\n" \
                       f"🚀 Speed: {speed_mbps:.2f} MB/s"
                asyncio.run_coroutine_threadsafe(safe_edit(text), loop)

        def ftp_upload_task():
            ftp = ftplib.FTP(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            
            # Auto-create folder cPanel
            for d in FTP_DIR.split('/'):
                if d:
                    try: ftp.cwd(d)
                    except ftplib.error_perm:
                        ftp.mkd(d)
                        ftp.cwd(d)

            # Upload file menggunakan URL Encode untuk spasi agar aman di URL browser nanti
            # Tapi nyimpan di FTP tetap pakai spasi sesuai request lu
            with open(file_path, "rb") as file:
                ftp.storbinary(f"STOR {file_name}", file, callback=ftp_callback)
            ftp.quit()

        # Jalankan FTP secara paralel (aman buat multi-file)
        await asyncio.to_thread(ftp_upload_task)
        
        # Bersihkan memori HP
        os.remove(file_path)

        # ================= 4. HASIL AKHIR (FONT MONO) =================
        # URL encode spasinya biar linknya bisa diklik langsung di Telegram
        file_url = f"{DOMAIN}/{file_name.replace(' ', '%20')}"
        final_mb = total_size / (1024 * 1024)
        
        await status_msg.edit_text(
            f"✅ **SUKSES MASUK HOSTING!**\n\n"
            f"📂 Nama File :\n`{file_name}`\n\n"
            f"📏 Ukuran File :\n`{final_mb:.2f} MB`\n\n"
            f"🔗 Link Download :\n`{file_url}`"
        )
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error Terjadi: {e}")

print("Bot Pyrogram Final Aktif: Auto Format Nama '(Modora)', Mono Font, Multi-File Processing!")
app.run()
