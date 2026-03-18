import telebot
import requests

TOKEN = "8586628406:AAHvCTHTz1erJTiB_9RrxVcrEawWcqmfc_k"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot aktif. Kirimkan file (dokumen, foto, video, atau audio) untuk diupload ke hosting.")

@bot.message_handler(content_types=['document', 'photo', 'audio', 'video'])
def handle_file(message):
    bot.reply_to(message, "⏳ Sedang memproses dan mengupload file...")
    try:
        # Ambil ID dan tentukan nama file agar server hosting mau menerima
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_name = "photo.jpg"
        elif message.content_type == 'video':
            file_id = message.video.file_id
            file_name = "video.mp4"
        else:
            file_id = message.audio.file_id
            file_name = "audio.mp3"

        # Download file dari Telegram
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Upload ke Catbox.moe (lebih stabil)
        response = requests.post(
            'https://catbox.moe/user/api.php',
            data={'reqtype': 'fileupload'},
            files={'fileToUpload': (file_name, downloaded_file)}
        )
        
        # Cek apakah responnya berupa link valid (berawalan https)
        if response.text.startswith('https'):
            bot.reply_to(message, f"✅ Sukses!\n🔗 Link download: {response.text}")
        else:
            bot.reply_to(message, f"❌ Gagal mengupload file. Server menjawab: {response.text}")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {e}")

print("Membersihkan sisa Webhook lama...")
bot.remove_webhook()

print("Bot sedang berjalan...")
bot.infinity_polling()
