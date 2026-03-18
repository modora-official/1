from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# Penyimpanan sementara status user buat ganti nama file
pending_files = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Bot aktif dengan mesin Pyrogram!\nGas kirim file apapun, nanti akan ada opsi buat ganti nama.")

# Nangkep file yang dikirim
@app.on_message(filters.document | filters.photo | filters.video | filters.audio)
async def ask_rename(client, message):
    chat_id = message.chat.id
    # Simpan file ke memori sementara bot
    pending_files[chat_id] = {"msg": message, "status": "WAITING_CHOICE"}
    
    # Bikin tombol pilihan
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ya", callback_data="rename_ya"),
         InlineKeyboardButton("❌ Tidak (Pakai nama asli)", callback_data="rename_tidak")]
    ])
    await message.reply_text("Apakah lu mau custom nama file ini?", reply_markup=keyboard)

# Nangkep pencetan tombol
@app.on_callback_query()
async def button_handler(client, query):
    chat_id = query.message.chat.id
    if chat_id not in pending_files:
        await query.answer("Waktu habis atau file tidak ditemukan. Kirim ulang filenya.", show_alert=True)
        return

    if query.data == "rename_tidak":
        await query.message.edit_text("⏳ Oke, menggunakan nama asli. Memulai proses...")
        await process_upload(client, chat_id, custom_name=None, status_msg=query.message)
    
    elif query.data == "rename_ya":
        pending_files[chat_id]["status"] = "WAITING_NAME"
        await query.message.edit_text("✍️ Silakan ketik nama file barunya (Contoh: `aplikasi_mod.apk` atau `video_lucu.mp4`).\n\n*Catatan: Pastikan jangan pakai spasi, ganti spasi pakai garis bawah (_).*")

# Nangkep balasan teks (kalau dia pilih ganti nama)
@app.on_message(filters.text & ~filters.command("start"))
async def text_handler(client, message):
    chat_id = message.chat.id
    if chat_id in pending_files and pending_files[chat_id]["status"] == "WAITING_NAME":
        new_name = message.text.replace(" ", "_")
        status_msg = await message.reply_text(f"⏳ Nama file diatur menjadi: **{new_name}**. Memulai proses...")
        await process_upload(client, chat_id, custom_name=new_name, status_msg=status_msg)

# Fungsi utama buat Download & Upload dengan Speedometer
async def process_upload(client, chat_id, custom_name, status_msg):
    file_message = pending_files[chat_id]["msg"]
    del pending_files[chat_id] # Hapus dari antrean
    
    try:
        # ================= 1. PROSES DOWNLOAD =================
        start_dl_time = time.time()
        last_dl_update = [time.time()] # Pakai list biar bisa diubah di dalam fungsi

        async def down_progress(current, total):
            now = time.time()
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
                       f"🚀 Kecepatan: {speed_mbps:.2f} MB/s"
                try: await status_msg.edit_text(text)
                except Exception: pass

        file_path = await file_message.download(progress=down_progress)
        
        if not file_path:
            await status_msg.edit_text("❌ Gagal mendownload file dari Telegram.")
            return

        # ================= 2. SETTING NAMA FILE =================
        if custom_name:
            file_name = custom_name
            # Tambahin ekstensi asli kalau user lupa ngetik
            if not os.path.splitext(file_name)[1]:
                file_name += os.path.splitext(file_path)[1]
        else:
            file_name = os.path.basename(file_path)

        await status_msg.edit_text(f"✅ Download 100%. Menyiapkan koneksi ke cPanel...\n📂 Nama file: {file_name}")
        
        # ================= 3. PROSES UPLOAD FTP =================
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
                       f"🚀 Kecepatan: {speed_mbps:.2f} MB/s"
                asyncio.run_coroutine_threadsafe(safe_edit(text), loop)

        def ftp_upload_task():
            ftp = ftplib.FTP(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            
            # Buat folder jika belum ada
            for d in FTP_DIR.split('/'):
                if d:
                    try: ftp.cwd(d)
                    except ftplib.error_perm:
                        ftp.mkd(d)
                        ftp.cwd(d)

            with open(file_path, "rb") as file:
                ftp.storbinary(f"STOR {file_name}", file, callback=ftp_callback)
            ftp.quit()

        # Jalankan FTP pakai background thread biar gak ngelag
        await asyncio.to_thread(ftp_upload_task)

        # Hapus file lokal di HP
        os.remove(file_path)

        # Hasil Akhir
        file_url = f"{DOMAIN}/{file_name}"
        await status_msg.edit_text(f"✅ **SUKSES MASUK HOSTING!**\n\n📂 Nama File: {file_name}\n🔗 Link: {file_url}")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error Terjadi: {e}")

print("Bot Pyrogram V3 aktif: Fitur Tombol Rename & Speedometer MB/s berjalan!")
app.run()
