import os
import telebot
from telebot.types import InputMediaPhoto
from supabase import create_client, Client
from dotenv import load_dotenv
from flask import Flask
import threading

# --- 1. CẤU HÌNH HỆ THỐNG ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bộ nhớ tạm để lưu ảnh khi đang chat thêm phòng
user_data = {}

# --- 2. CẤU HÌNH WEB SERVER GIẢ (CHO RENDER) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot quản lý phòng trọ đang hoạt động 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- 3. CÁC TÍNH NĂNG CỦA BOT ---

# Lệnh /start - Hướng dẫn sử dụng
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    huong_dan = (
        "🤖 *CHÀO MỪNG BẠN ĐẾN VỚI TRỢ LÝ PHÒNG TRỌ*\n\n"
        "Hãy dùng các lệnh sau để làm việc:\n"
        "👉 `/themphong` : Thêm một phòng mới vào kho\n"
        "👉 `/tim <từ khóa>` : Tìm phòng theo Quận, Đường, Giá\n"
        "👉 Gõ trực tiếp *Mã phòng* để lấy nhanh thông tin.\n\n"
        "Ví dụ: `/tim Q10` hoặc `/tim 5 Triệu`"
    )
    bot.send_message(message.chat.id, huong_dan, parse_mode="Markdown")

# Lệnh /themphong - Bắt đầu quy trình thêm phòng
@bot.message_handler(commands=['themphong'])
def bat_dau_them_phong(message):
    msg = bot.reply_to(message, "📸 *Bước 1:* Hãy gửi cho tôi 1 bức ảnh của phòng trọ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, nhan_anh_phong)

def nhan_anh_phong(message):
    if not message.photo:
        bot.reply_to(message, "❌ Đây không phải là ảnh. Vui lòng gõ lại lệnh /themphong để bắt đầu lại.")
        return
    
    # Lấy mã ảnh lớn nhất
    file_id = message.photo[-1].file_id
    user_data[message.chat.id] = {'file_id': file_id}
    
    huong_dan_nhap = (
        "✅ Đã nhận ảnh! \n\n"
        "📝 *Bước 2:* Hãy nhập thông tin phòng theo đúng cú pháp sau (ngăn cách bằng dấu gạch ngang `-`):\n\n"
        "`Mã phòng - Địa chỉ - Giá - Tình trạng`\n\n"
        "*Ví dụ:* `Q10-002 - 123 Sư Vạn Hạnh, Q10 - 5.5 Triệu - Trống`"
    )
    msg = bot.reply_to(message, huong_dan_nhap, parse_mode="Markdown")
    bot.register_next_step_handler(msg, luu_phong_vao_kho)

def luu_phong_vao_kho(message):
    thong_tin = message.text.split('-')
    if len(thong_tin) != 4:
        bot.reply_to(message, "❌ Nhập sai cú pháp! Vui lòng gõ lại lệnh /themphong để thử lại.")
        return
    
    ma_phong = thong_tin[0].strip().upper()
    dia_chi = thong_tin[1].strip()
    gia = thong_tin[2].strip()
    tinh_trang = thong_tin[3].strip()
    file_id_anh = user_data[message.chat.id]['file_id']
    
    try:
        data = {
            "ma_phong": ma_phong,
            "dia_chi": dia_chi,
            "gia": gia,
            "tinh_trang": tinh_trang,
            "file_id_anh": file_id_anh
        }
        supabase.table("phong_tro").insert(data).execute()
        bot.reply_to(message, f"🎉 *THÊM PHÒNG THÀNH CÔNG!*\n\nMã phòng: {ma_phong} đã có trong kho.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Lỗi khi lưu vào kho: {e}")

# Lệnh /tim - Tìm kiếm tổng hợp
@bot.message_handler(commands=['tim'])
def tim_kiem_tong_hop(message):
    tu_khoa = message.text.replace('/tim', '').strip().lower()
    if not tu_khoa:
        bot.reply_to(message, "⚠️ Bạn chưa nhập từ khóa. Ví dụ: `/tim Q10` hoặc `/tim 5 Triệu`", parse_mode="Markdown")
        return
        
    bot.reply_to(message, f"🔍 Đang tìm các phòng có chứa từ '{tu_khoa}'...")
    
    try:
        # Lấy toàn bộ phòng về (phù hợp cho kho < 5000 phòng)
        response = supabase.table("phong_tro").select("*").execute()
        danh_sach = response.data
        
        ket_qua = []
        for p in danh_sach:
            # Tìm trong mã phòng, địa chỉ hoặc giá
            if (tu_khoa in p.get('ma_phong', '').lower() or 
                tu_khoa in p.get('dia_chi', '').lower() or 
                tu_khoa in p.get('gia', '').lower()):
                ket_qua.append(p)
                
        if len(ket_qua) == 0:
            bot.send_message(message.chat.id, "❌ Không tìm thấy phòng nào phù hợp với yêu cầu.")
        else:
            bot.send_message(message.chat.id, f"✅ Đã tìm thấy *{len(ket_qua)}* phòng phù hợp:", parse_mode="Markdown")
            for phong in ket_qua:
                thong_tin = (
                    f"🏠 *Mã:* {phong['ma_phong']}\n"
                    f"📍 *Địa chỉ:* {phong['dia_chi']}\n"
                    f"💰 *Giá:* {phong['gia']}\n"
                    f"✅ *Tình trạng:* {phong['tinh_trang']}"
                )
                if phong.get('file_id_anh'):
                    # Lấy ảnh đầu tiên nếu có nhiều ảnh
                    anh_dau = phong['file_id_anh'].split(',')[0].strip()
                    bot.send_photo(message.chat.id, photo=anh_dau, caption=thong_tin, parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, thong_tin, parse_mode="Markdown")
                    
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi tìm kiếm: {e}")

# Lấy nhanh bằng mã phòng (Nhập text bình thường không có dấu /)
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def lay_nhanh_ma_phong(message):
    tu_khoa = message.text.strip().upper()
    try:
        response = supabase.table("phong_tro").select("*").eq("ma_phong", tu_khoa).execute()
        if len(response.data) > 0:
            phong = response.data[0]
            thong_tin = (f"🏠 *Mã:* {phong['ma_phong']}\n📍 *Địa chỉ:* {phong['dia_chi']}\n"
                         f"💰 *Giá:* {phong['gia']}\n✅ *Tình trạng:* {phong['tinh_trang']}")
            if phong.get('file_id_anh'):
                anh_dau = phong['file_id_anh'].split(',')[0].strip()
                bot.send_photo(message.chat.id, photo=anh_dau, caption=thong_tin, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, thong_tin, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Không tìm thấy mã phòng này! (Gõ /tim <từ khóa> để tìm tương đối)")
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Lỗi kết nối dữ liệu.")

# --- 4. KHỞI ĐỘNG HỆ THỐNG ---
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("✅ Bot và Web Server đang chạy...")
    bot.infinity_polling()