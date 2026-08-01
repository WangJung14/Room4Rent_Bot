import os
import telebot
from telebot.types import InputMediaPhoto
from supabase import create_client, Client
from dotenv import load_dotenv

# Tải biến môi trường từ file .env (khi chạy ở máy tính)
load_dotenv()

# Lấy thông tin bảo mật một cách an toàn
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@bot.message_handler(content_types=['photo'])
def get_photo_id(message):
    file_id = message.photo[-1].file_id
    bot.reply_to(message, f"Mã ảnh của bạn là:\n`{file_id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def search_room(message):
    tu_khoa = message.text.strip().upper()
    bot.send_message(message.chat.id, f"🔍 Đang tìm phòng: {tu_khoa}...")

    try:
        response = supabase.table("phong_tro").select("*").eq("ma_phong", tu_khoa).execute()
        danh_sach = response.data

        if len(danh_sach) > 0:
            phong = danh_sach[0]
            thong_tin = (
                f"🏠 *Mã phòng:* {phong['ma_phong']}\n"
                f"📍 *Địa chỉ:* {phong['dia_chi']}\n"
                f"💰 *Giá:* {phong['gia']}\n"
                f"✅ *Tình trạng:* {phong['tinh_trang']}"
            )
            
            chuoi_anh = phong.get('file_id_anh', '')
            if chuoi_anh:
                danh_sach_anh = [anh.strip() for anh in chuoi_anh.split(',') if anh.strip()]
                if len(danh_sach_anh) == 1:
                    bot.send_photo(message.chat.id, photo=danh_sach_anh[0], caption=thong_tin, parse_mode="Markdown")
                else:
                    media_group = [InputMediaPhoto(anh_id, caption=thong_tin if i == 0 else None, parse_mode="Markdown") for i, anh_id in enumerate(danh_sach_anh)]
                    bot.send_media_group(message.chat.id, media=media_group)
            else:
                bot.send_message(message.chat.id, thong_tin, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Không tìm thấy mã phòng này trong kho!")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi kết nối dữ liệu: {e}")

print("✅ Bot đang chạy...")
bot.infinity_polling()