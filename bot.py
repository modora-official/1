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
        if message.content_type == 'document':
            file_id = message.document.file_id
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'video':
            file_id = message.video.file_id
        else:
            file_id = message.audio.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        response = requests.post('https://file.io', files={'file': downloaded_file})
        
        if response.status_code == 200:
            link = response.json().get('link')
            bot.reply_to(message, f"✅ Sukses!\n🔗 Link download: {link}")
        else:
            bot.reply_to(message, "❌ Gagal mengupload file ke hosting.")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {e}")

print("Membersihkan sisa Webhook lama...")
bot.remove_webhook()

print("Bot sedang berjalan...")
bot.infinity_polling()
