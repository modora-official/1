import telebot
import ftplib
from io import BytesIO

TOKEN = "8586628406:AAHvCTHTz1erJTiB_9RrxVcrEawWcqmfc_k"
bot = telebot.TeleBot(TOKEN)

# ================= KONFIGURASI HOSTING =================
FTP_HOST = "denali.iixcp.rumahweb.net"
FTP_USER = "modorazo"
FTP_PASS = "@Anjir!999" 
FTP_DIR = "public_html/RNDM" 
DOMAIN = "https://modorazone.it.com/RNDM"
# =======================================================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot aktif! Kirim file dan bot akan langsung menguploadnya ke cPanel lu.\n\n⚠️ Catatan: Limit maksimal file dari Telegram adalah 20MB.")

@bot.message_handler(content_types=['document', 'photo', 'audio', 'video'])
def handle_file(message):
    bot.reply_to(message, "⏳ Memproses dan mengupload ke cPanel...")
    try:
        # Tentukan ukuran file dan nama file
        file_size = 0
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name
            file_size = message.document.file_size
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_name = f"photo_{file_id[:10]}.jpg"
            file_size = message.photo[-1].file_size
        elif message.content_type == 'video':
            file_id = message.video.file_id
            file_name = f"video_{file_id[:10]}.mp4"
            file_size = message.video.file_size
        else:
            file_id = message.audio.file_id
            file_name = f"audio_{file_id[:10]}.mp3"
            file_size = message.audio.file_size

        # Cek limit API Telegram (20 MB = 20 * 1024 * 1024 bytes = 20971520 bytes)
        if file_size and file_size > 20971520:
            bot.reply_to(message, f"❌ Gagal: File terlalu besar!\n\nUkuran file lu: {round(file_size/1024/1024, 2)} MB.\nLimit resmi Telegram Bot maksimal cuma 20 MB.")
            return

        # Download dari Telegram
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Proses Upload via FTP ke cPanel
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        
        # Buat folder otomatis jika belum ada
        dirs = FTP_DIR.split('/')
        for d in dirs:
            if d: # Abaikan string kosong
                try:
                    ftp.cwd(d) # Coba masuk ke folder
                except ftplib.error_perm:
                    ftp.mkd(d) # Kalau gagal (belum ada), buat foldernya
                    ftp.cwd(d) # Lalu masuk ke folder yang baru dibuat

        # Upload file ke server
        bio = BytesIO(downloaded_file)
        ftp.storbinary(f"STOR {file_name}", bio)
        ftp.quit()

        # Kasih link ke user
        file_url = f"{DOMAIN}/{file_name}"
        bot.reply_to(message, f"✅ Berhasil masuk ke Hosting!\n🔗 Link: {file_url}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error FTP/Upload: {e}")

print("Membersihkan Webhook...")
bot.remove_webhook()

print("Bot berjalan dan terhubung ke cPanel...")
bot.infinity_polling()
