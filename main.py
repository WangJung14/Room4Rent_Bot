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

# Bộ nhớ tạm để quản lý trạng thái khi người dùng gửi nhiều ảnh
user_state = {}   # Trạng thái hiện tại: Đang làm gì?
user_photos = {}  # Danh sách các ID ảnh đang chờ lưu

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
        "👉 `/themphong` : Thêm phòng mới (hỗ trợ nhiều ảnh)\n"
        "👉 `/tim <từ khóa>` : Tìm phòng theo Quận, Đường, Giá\n"
        "👉 `/huy` : Hủy thao tác đang làm dở\n"
        "👉 Gõ trực tiếp *Mã phòng* để lấy nhanh thông tin."
    )
    bot.send_message(message.chat.id, huong_dan, parse_mode="Markdown")

# Lệnh /huy - Hủy thao tác thêm phòng
@bot.message_handler(commands=['huy'])
def huy_thao_tac(message):
    chat_id = message.chat.id
    user_state.pop(chat_id, None)
    user_photos.pop(chat_id, None)
    bot.send_message(chat_id, "✅ Đã hủy thao tác. Bot đã trở về trạng thái bình thường.")

# Lệnh /themphong - Bắt đầu quy trình
@bot.message_handler(commands=['themphong'])
def bat_dau_them_phong(message):
    chat_id = message.chat.id
    user_state[chat_id] = 'dang_cho_anh'
    user_photos[chat_id] = [] # Khởi tạo danh sách ảnh rỗng
    
    huong_dan = (
        "📸 *CHẾ ĐỘ THÊM PHÒNG*\n\n"
        "*Bước 1:* Hãy gửi cho tôi TẤT CẢ ảnh của phòng trọ (có thể chọn gửi nhiều ảnh cùng lúc).\n\n"
        "*Bước 2:* Sau khi ảnh tải xong hết, hãy nhập thông tin phòng theo cú pháp:\n"
        "`Mã phòng - Địa chỉ - Giá - Tình trạng`\n\n"
        "*(Nếu muốn thoát, hãy gõ /huy)*"
    )
    bot.send_message(chat_id, huong_dan, parse_mode="Markdown")

# Bắt sự kiện người dùng gửi ảnh
@bot.message_handler(content_types=['photo'])
def nhan_nhieu_anh(message):
    chat_id = message.chat.id
    # Chỉ gom ảnh nếu đang ở chế độ thêm phòng
    if user_state.get(chat_id) == 'dang_cho_anh':
        file_id = message.photo[-1].file_id
        user_photos[chat_id].append(file_id)
        # Lưu ý: Không nhắn tin phản hồi ở đây để tránh bị spam khi người dùng gửi 10 ảnh cùng lúc

# Xử lý toàn bộ tin nhắn chữ (Bao gồm nhập thông tin kho và tìm kiếm mã phòng)
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def xu_ly_text_chung(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    # KỊCH BẢN 1: NGƯỜI DÙNG ĐANG TRONG QUÁ TRÌNH THÊM PHÒNG
    if user_state.get(chat_id) == 'dang_cho_anh':
        # Phân tách thông tin bằng dấu gạch ngang
        thong_tin = text.split('-')
        
        # Nếu nhập đúng 4 cụm từ
        if len(thong_tin) == 4:
            ma_phong = thong_tin[0].strip().upper()
            dia_chi = thong_tin[1].strip()
            gia = thong_tin[2].strip()
            tinh_trang = thong_tin[3].strip()
            
            danh_sach_anh = user_photos.get(chat_id, [])
            if len(danh_sach_anh) == 0:
                bot.send_message(chat_id, "❌ Bạn chưa gửi bức ảnh nào! Hãy gửi ít nhất 1 ảnh trước khi nhập thông tin.")
                return
            
            # Gom tất cả mã ảnh lại thành 1 chuỗi, cách nhau bằng dấu phẩy
            chuoi_anh = ",".join(danh_sach_anh)
            
            try:
                data = {
                    "ma_phong": ma_phong,
                    "dia_chi": dia_chi,
                    "gia": gia,
                    "tinh_trang": tinh_trang,
                    "file_id_anh": chuoi_anh
                }
                supabase.table("phong_tro").insert(data).execute()
                bot.send_message(chat_id, f"🎉 *THÊM PHÒNG THÀNH CÔNG!*\n\nĐã lưu mã {ma_phong} cùng với {len(danh_sach_anh)} bức ảnh. Bot đã trở về trạng thái bình thường.", parse_mode="Markdown")
                
                # Reset trạng thái
                user_state.pop(chat_id, None)
                user_photos.pop(chat_id, None)
            except Exception as e:
                bot.send_message(chat_id, f"⚠️ Lỗi khi lưu vào kho: {e}")
            return
        else:
            bot.send_message(chat_id, "❌ Nhập sai cú pháp! Hãy nhập đúng định dạng:\n`Mã - Địa chỉ - Giá - Tình trạng`\nHoặc gõ /huy để thoát.", parse_mode="Markdown")
            return

    # KỊCH BẢN 2: TÌM KIẾM THEO MÃ PHÒNG (BÌNH THƯỜNG)
    tu_khoa = text.upper()
    try:
        response = supabase.table("phong_tro").select("*").eq("ma_phong", tu_khoa).execute()
        if len(response.data) > 0:
            phong = response.data[0]
            thong_tin = (f"🏠 *Mã:* {phong['ma_phong']}\n📍 *Địa chỉ:* {phong['dia_chi']}\n"
                         f"💰 *Giá:* {phong['gia']}\n✅ *Tình trạng:* {phong['tinh_trang']}")
            
            chuoi_anh = phong.get('file_id_anh', '')
            if chuoi_anh:
                danh_sach_anh = [anh.strip() for anh in chuoi_anh.split(',') if anh.strip()]
                if len(danh_sach_anh) == 1:
                    bot.send_photo(chat_id, photo=danh_sach_anh[0], caption=thong_tin, parse_mode="Markdown")
                else:
                    # Gửi nhiều ảnh cùng lúc (MediaGroup)
                    media_group = [InputMediaPhoto(anh_id, caption=thong_tin if i == 0 else None, parse_mode="Markdown") for i, anh_id in enumerate(danh_sach_anh)]
                    bot.send_media_group(chat_id, media=media_group)
            else:
                bot.send_message(chat_id, thong_tin, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ Không tìm thấy mã phòng này! (Gõ /tim <từ khóa> để tìm tương đối)")
    except Exception:
        bot.send_message(chat_id, "⚠️ Lỗi kết nối dữ liệu.")

# Lệnh /tim - Tìm kiếm tổng hợp
@bot.message_handler(commands=['tim'])
def tim_kiem_tong_hop(message):
    tu_khoa = message.text.replace('/tim', '').strip().lower()
    if not tu_khoa:
        bot.reply_to(message, "⚠️ Bạn chưa nhập từ khóa. Ví dụ: `/tim Q10` hoặc `/tim 5 Triệu`", parse_mode="Markdown")
        return
        
    bot.reply_to(message, f"🔍 Đang tìm các phòng có chứa từ '{tu_khoa}'...")
    try:
        response = supabase.table("phong_tro").select("*").execute()
        danh_sach = response.data
        ket_qua = []
        for p in danh_sach:
            if (tu_khoa in p.get('ma_phong', '').lower() or 
                tu_khoa in p.get('dia_chi', '').lower() or 
                tu_khoa in p.get('gia', '').lower()):
                ket_qua.append(p)
                
        if len(ket_qua) == 0:
            bot.send_message(message.chat.id, "❌ Không tìm thấy phòng nào phù hợp với yêu cầu.")
        else:
            bot.send_message(message.chat.id, f"✅ Đã tìm thấy *{len(ket_qua)}* phòng phù hợp:", parse_mode="Markdown")
            for phong in ket_qua:
                thong_tin = (f"🏠 *Mã:* {phong['ma_phong']}\n📍 *Địa chỉ:* {phong['dia_chi']}\n"
                             f"💰 *Giá:* {phong['gia']}\n✅ *Tình trạng:* {phong['tinh_trang']}")
                if phong.get('file_id_anh'):
                    anh_dau = phong['file_id_anh'].split(',')[0].strip()
                    bot.send_photo(message.chat.id, photo=anh_dau, caption=thong_tin, parse_mode="Markdown")
                else:
                    bot.send_message(message.chat.id, thong_tin, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi tìm kiếm: {e}")

# --- 4. KHỞI ĐỘNG HỆ THỐNG ---
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("✅ Bot và Web Server đang chạy...")
    bot.infinity_polling()