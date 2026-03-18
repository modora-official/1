from pyrogram import Client, filters
import ftplib
import os

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

# Inisialisasi Bot Pyrogram
app = Client("upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("Bot aktif dengan mesin Pyrogram! Gas kirim file APK atau video berukuran besar, bot akan langsung menguploadnya ke cPanel.")

@app.on_message(filters.document | filters.photo | filters.video | filters.audio)
def handle_file(client, message):
    msg = message.reply_text("⏳ Memproses file... (Tunggu sebentar kalau filenya gede)")
    
    try:
        # Download file dari Telegram ke Termux
        msg.edit_text("⏳ Sedang mendownload file dari Telegram ke Termux...")
        file_path = message.download()
        
        if not file_path:
            msg.edit_text("❌ Gagal mendownload file.")
            return

        file_name = os.path.basename(file_path)

        # Proses Upload via FTP ke cPanel
        msg.edit_text("☁️ Sedang mengupload file ke cPanel Rumahweb...")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        
        # Buat folder otomatis jika belum ada
        dirs = FTP_DIR.split('/')
        for d in dirs:
            if d:
                try:
                    ftp.cwd(d)
                except ftplib.error_perm:
                    ftp.mkd(d)
                    ftp.cwd(d)

        # Upload file ke server
        with open(file_path, "rb") as file:
            ftp.storbinary(f"STOR {file_name}", file)
        
        ftp.quit()

        # Hapus file lokal di Termux agar memori HP aman
        os.remove(file_path)

        # Kasih link ke user
        file_url = f"{DOMAIN}/{file_name}"
        msg.edit_text(f"✅ Berhasil masuk ke Hosting!\n🔗 Link: {file_url}")
            
    except Exception as e:
        msg.edit_text(f"❌ Error FTP/Upload: {e}")

print("Bot Pyrogram berjalan dan siap menerima file besar...")
app.run()
