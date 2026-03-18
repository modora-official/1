import telebot
import ftplib
from io import BytesIO

TOKEN = "8586628406:AAHvCTHTz1erJTiB_9RrxVcrEawWcqmfc_k"
bot = telebot.TeleBot(TOKEN)

# ================= KONFIGURASI HOSTING =================
FTP_HOST = "denali.iixcp.rumahweb.net"
FTP_USER = "modorazo"
# ISI PASSWORD LU DI BAWAH INI SEBELUM DIJALANKAN!
FTP_PASS = "@Anjir!999" 
# Folder tempat file web disimpan (biasanya public_html)
FTP_DIR = "public_html/RNDM" 
DOMAIN = "https://modorazone.it.com/RNDM"
# =======================================================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot aktif! Kirim file dan bot akan langsung menguploadnya ke cPanel lu.")

@bot.message_handler(content_types=['document', 'photo', 'audio', 'video'])
def handle_file(message):
    bot.reply_to(message, "⏳ Memproses dan mengupload ke cPanel...")
    try:
        # Tentukan nama file
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_name = f"photo_{file_id[:10]}.jpg"
        elif message.content_type == 'video':
            file_id = message.video.file_id
            file_name = f"video_{file_id[:10]}.mp4"
        else:
            file_id = message.audio.file_id
            file_name = f"audio_{file_id[:10]}.mp3"

        # Download dari Telegram
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Proses Upload via FTP ke cPanel
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        
        # Pindah ke folder target
        try:
            ftp.cwd(FTP_DIR)
        except Exception as e:
            bot.reply_to(message, f"⚠️ Gagal masuk ke folder {FTP_DIR}. Pastikan foldernya udah dibuat di cPanel!\nError: {e}")
            ftp.quit()
            return

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
