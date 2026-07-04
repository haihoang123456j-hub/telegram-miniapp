# ===========================
# BOT TELEGRAM - FULL (v4 - Khoá/mở tài khoản + Backup)
# ===========================

import sqlite3
import random
import shutil
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ===========================
# THAY TOKEN CỦA BẠN
# ===========================
TOKEN = "DÁN_TOKEN_CỦA_BẠN"

# ID Telegram của admin (dùng @userinfobot để lấy)
ADMIN_ID = 123456789

# ===========================
# CẤU HÌNH MỜI BẠN
# ===========================
THUONG_MOI_BAN = 20000
PHAN_TRAM_HOA_HONG = 5

# ===========================
# DANH SÁCH DANH HIỆU NỘI BỘ
# ===========================
DANH_HIEU_SHOP = [
    ("⭐ Tân Binh", 5000),
    ("🔥 Chăm Chỉ", 20000),
    ("💎 Đại Gia", 50000),
    ("👑 Huyền Thoại", 100000),
    ("🐉 Bất Tử", 300000),
]

# ===========================
# DATABASE
# ===========================

db = sqlite3.connect("database.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    balance INTEGER DEFAULT 100000,
    created TEXT,
    last_daily TEXT,
    streak INTEGER DEFAULT 0,
    danh_hieu TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS giftcodes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    denomination INTEGER,
    code TEXT,
    used INTEGER DEFAULT 0,
    used_by INTEGER,
    used_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    loai TEXT,
    so_tien INTEGER,
    mo_ta TEXT,
    thoi_gian TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS cuoc(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nguoi_thach INTEGER,
    doi_thu INTEGER,
    so_tien INTEGER,
    trang_thai TEXT DEFAULT 'cho',
    thoi_gian TEXT
)
""")

db.commit()

for cot, dinh_nghia in [
    ("last_daily", "TEXT"),
    ("streak", "INTEGER DEFAULT 0"),
    ("danh_hieu", "TEXT"),
    ("referred_by", "INTEGER"),
    ("bi_khoa", "INTEGER DEFAULT 0"),
]:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {cot} {dinh_nghia}")
        db.commit()
    except sqlite3.OperationalError:
        pass

# ===========================
# HÀM GHI LỊCH SỬ GIAO DỊCH
# ===========================

def ghi_lich_su(user_id, loai, so_tien, mo_ta):
    cur.execute(
        "INSERT INTO transactions (user_id, loai, so_tien, mo_ta, thoi_gian) VALUES (?,?,?,?,?)",
        (user_id, loai, so_tien, mo_ta, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    )
    db.commit()


def cong_tru_tien(user_id, so_tien):
    cur.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        return None
    balance_moi = row[0] + so_tien
    cur.execute("UPDATE users SET balance=? WHERE id=?", (balance_moi, user_id))
    db.commit()
    return balance_moi


def kiem_tra_bi_khoa(user_id):
    """Trả về True nếu user đang bị khoá."""
    cur.execute("SELECT bi_khoa FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        return False
    return row[0] == 1

# ===========================
# MENU
# ===========================

def menu():

    keyboard = [
        [
            InlineKeyboardButton("👤 Hồ sơ", callback_data="profile"),
            InlineKeyboardButton("💰 Ví", callback_data="wallet")
        ],
        [
            InlineKeyboardButton("🎁 Điểm danh", callback_data="daily"),
            InlineKeyboardButton("📊 Thống kê", callback_data="stats")
        ],
        [
            InlineKeyboardButton("🏆 Xếp hạng", callback_data="rank_menu"),
            InlineKeyboardButton("🎫 Đổi thẻ", callback_data="doithe_menu")
        ],
        [
            InlineKeyboardButton("🎖️ Đổi thưởng", callback_data="danhhieu_menu"),
            InlineKeyboardButton("⚔️ PvP Cược", callback_data="pvp_help")
        ],
        [
            InlineKeyboardButton("👥 Mời bạn", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("⚙️ Cài đặt", callback_data="setting"),
            InlineKeyboardButton("❓ Trợ giúp", callback_data="help")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def nut_quay_lai(callback_data="home"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Quay lại", callback_data=callback_data)]
    ])

# ===========================
# START (có xử lý link mời bạn + kiểm tra khoá)
# ===========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    cur.execute(
        "SELECT * FROM users WHERE id=?",
        (user.id,)
    )

    data = cur.fetchone()

    if data is None:

        nguoi_gioi_thieu = None

        if context.args:
            try:
                ma_gioi_thieu = int(context.args[0])
                if ma_gioi_thieu != user.id:
                    cur.execute("SELECT id FROM users WHERE id=?", (ma_gioi_thieu,))
                    if cur.fetchone() is not None:
                        nguoi_gioi_thieu = ma_gioi_thieu
            except ValueError:
                nguoi_gioi_thieu = None

        cur.execute(
            "INSERT INTO users (id,name,username,balance,created,last_daily,streak,danh_hieu,referred_by,bi_khoa) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                user.id,
                user.first_name,
                user.username,
                100000,
                datetime.now().strftime("%d/%m/%Y"),
                None,
                0,
                None,
                nguoi_gioi_thieu,
                0
            )
        )

        db.commit()

        if nguoi_gioi_thieu is not None:

            balance_moi = cong_tru_tien(nguoi_gioi_thieu, THUONG_MOI_BAN)

            ghi_lich_su(
                nguoi_gioi_thieu,
                "thuong_moi_ban",
                THUONG_MOI_BAN,
                f"Mời được {user.first_name} tham gia"
            )

            try:
                await context.bot.send_message(
                    chat_id=nguoi_gioi_thieu,
                    text=(
                        f"🎉 Bạn vừa mời thành công {user.first_name}!\n\n"
                        f"💰 Thưởng: +{THUONG_MOI_BAN:,} VNĐ\n"
                        f"💵 Số dư mới: {balance_moi:,} VNĐ"
                    )
                )
            except Exception:
                pass

    else:
        if kiem_tra_bi_khoa(user.id):
            await update.message.reply_text(
                "⛔ Tài khoản của bạn đã bị khoá.\n\n"
                "Liên hệ quản trị viên nếu bạn cho rằng đây là nhầm lẫn."
            )
            return

    text = f"""
╔══════════════════════╗
🚀 VIP DASHBOARD
╚══════════════════════╝

👋 Xin chào {user.first_name}

🟢 Trạng thái : Online

✨ Chọn chức năng bên dưới.
"""

    await update.message.reply_text(
        text,
        reply_markup=menu()
    )

# ===========================
# LỆNH THÁCH ĐẤU PVP
# ===========================

async def thach_dau(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if kiem_tra_bi_khoa(user.id):
        await update.message.reply_text("⛔ Tài khoản của bạn đã bị khoá.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Cú pháp: /thachdau <user_id> <số_tiền>\n"
            "Ví dụ: /thachdau 123456789 10000"
        )
        return

    try:
        doi_thu_id = int(context.args[0])
        so_tien = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ user_id và số tiền phải là số nguyên.")
        return

    if so_tien <= 0:
        await update.message.reply_text("⚠️ Số tiền cược phải lớn hơn 0.")
        return

    if doi_thu_id == user.id:
        await update.message.reply_text("⚠️ Không thể tự thách đấu chính mình.")
        return

    if kiem_tra_bi_khoa(doi_thu_id):
        await update.message.reply_text("⚠️ Đối thủ này đang bị khoá tài khoản, không thể thách đấu.")
        return

    cur.execute("SELECT balance FROM users WHERE id=?", (user.id,))
    balance_thach = cur.fetchone()[0]

    if balance_thach < so_tien:
        await update.message.reply_text(
            f"⚠️ Bạn không đủ tiền để cược {so_tien:,} VNĐ (số dư: {balance_thach:,} VNĐ)."
        )
        return

    cur.execute("SELECT balance, name FROM users WHERE id=?", (doi_thu_id,))
    doi_thu_data = cur.fetchone()

    if doi_thu_data is None:
        await update.message.reply_text("⚠️ Không tìm thấy đối thủ này (họ chưa /start bot).")
        return

    balance_doi_thu, ten_doi_thu = doi_thu_data

    cur.execute(
        "INSERT INTO cuoc (nguoi_thach, doi_thu, so_tien, trang_thai, thoi_gian) VALUES (?,?,?,?,?)",
        (user.id, doi_thu_id, so_tien, "cho", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    )
    db.commit()

    cuoc_id = cur.lastrowid

    await update.message.reply_text(
        f"⚔️ Đã gửi lời thách đấu tới {ten_doi_thu}!\n\n"
        f"💰 Mức cược: {so_tien:,} VNĐ\n"
        f"⏳ Đang chờ đối thủ phản hồi..."
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Đồng ý", callback_data=f"cuoc_dongy_{cuoc_id}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"cuoc_tuchoi_{cuoc_id}")
        ]
    ]

    try:
        await context.bot.send_message(
            chat_id=doi_thu_id,
            text=(
                f"⚔️ THÁCH ĐẤU!\n\n"
                f"👤 {user.first_name} thách đấu bạn\n"
                f"💰 Mức cược: {so_tien:,} VNĐ\n\n"
                f"Bạn có đồng ý không?"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.message.reply_text(
            "⚠️ Không thể gửi lời thách đấu (đối thủ có thể đã chặn bot)."
        )

# ===========================
# NÚT BẤM
# ===========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    # Chặn user bị khoá dùng mọi nút bấm (trừ khi admin đang thao tác qua lệnh riêng)
    if kiem_tra_bi_khoa(user.id):
        await query.edit_message_text("⛔ Tài khoản của bạn đã bị khoá, không thể sử dụng bot.")
        return

    if query.data == "profile":

        cur.execute(
            "SELECT balance,created,danh_hieu FROM users WHERE id=?",
            (user.id,)
        )

        balance, created, danh_hieu = cur.fetchone()

        text = f"""
👤 THÔNG TIN

🆔 ID : {user.id}

📛 Tên : {user.first_name}

🌐 Username : @{user.username}

🎖️ Danh hiệu : {danh_hieu if danh_hieu else "Chưa có"}

💰 Số dư : {balance:,} VNĐ

📅 Tham gia : {created}
"""

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "wallet":

        cur.execute(
            "SELECT balance FROM users WHERE id=?",
            (user.id,)
        )

        balance = cur.fetchone()[0]

        await query.edit_message_text(
            f"""
💰 VÍ TIỀN

Số dư hiện tại

{balance:,} VNĐ
""",
            reply_markup=nut_quay_lai()
        )

    elif query.data == "daily":

        hom_nay = datetime.now().strftime("%d/%m/%Y")

        cur.execute(
            "SELECT balance,last_daily,streak FROM users WHERE id=?",
            (user.id,)
        )

        balance, last_daily, streak = cur.fetchone()

        if last_daily == hom_nay:

            text = f"""
🎁 ĐIỂM DANH

⚠️ Bạn đã điểm danh hôm nay rồi!

💰 Số dư hiện tại: {balance:,} VNĐ
🔥 Chuỗi ngày: {streak} ngày

⏰ Quay lại vào ngày mai nhé.
"""

        else:

            lien_tuc = False
            if last_daily:
                try:
                    ngay_cu = datetime.strptime(last_daily, "%d/%m/%Y")
                    khoang_cach = (datetime.now() - ngay_cu).days
                    if khoang_cach == 1:
                        lien_tuc = True
                except ValueError:
                    lien_tuc = False

            streak_moi = streak + 1 if lien_tuc else 1

            thuong_co_ban = 10000
            thuong_streak = min(streak_moi * 1000, 50000)
            tong_thuong = thuong_co_ban + thuong_streak

            balance_moi = balance + tong_thuong

            cur.execute(
                "UPDATE users SET balance=?, last_daily=?, streak=? WHERE id=?",
                (balance_moi, hom_nay, streak_moi, user.id)
            )
            db.commit()

            ghi_lich_su(
                user.id,
                "diem_danh",
                tong_thuong,
                f"Điểm danh ngày {streak_moi} - nhận {tong_thuong:,} VNĐ"
            )

            text = f"""
🎁 ĐIỂM DANH THÀNH CÔNG!

💰 Nhận được: +{tong_thuong:,} VNĐ
   (Cơ bản {thuong_co_ban:,} + Streak {thuong_streak:,})

🔥 Chuỗi ngày: {streak_moi} ngày liên tiếp

💵 Số dư mới: {balance_moi:,} VNĐ

✨ Quay lại vào ngày mai để giữ chuỗi nhé!
"""

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "stats":
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        await query.edit_message_text(
            f"📊 Tổng người dùng: {total}",
            reply_markup=nut_quay_lai()
        )

    elif query.data == "rank_menu":

        keyboard = [
            [InlineKeyboardButton("💰 Top số dư", callback_data="rank_balance")],
            [InlineKeyboardButton("🔥 Top streak", callback_data="rank_streak")],
            [InlineKeyboardButton("⬅️ Quay lại", callback_data="home")]
        ]

        await query.edit_message_text(
            "🏆 BẢNG XẾP HẠNG\n\nChọn bảng bạn muốn xem:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "rank_balance":

        cur.execute(
            "SELECT name,balance FROM users ORDER BY balance DESC LIMIT 10"
        )
        ds = cur.fetchall()

        text = "💰 TOP SỐ DƯ CAO NHẤT\n\n"

        if not ds:
            text += "Chưa có dữ liệu."
        else:
            huy_hieu = ["🥇", "🥈", "🥉"]
            for i, (ten, balance) in enumerate(ds):
                hang = huy_hieu[i] if i < 3 else f"{i+1}."
                text += f"{hang} {ten} — {balance:,} VNĐ\n"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Quay lại", callback_data="rank_menu")]
            ])
        )

    elif query.data == "rank_streak":

        cur.execute(
            "SELECT name,streak FROM users ORDER BY streak DESC LIMIT 10"
        )
        ds = cur.fetchall()

        text = "🔥 TOP STREAK DÀI NHẤT\n\n"

        if not ds:
            text += "Chưa có dữ liệu."
        else:
            huy_hieu = ["🥇", "🥈", "🥉"]
            for i, (ten, streak) in enumerate(ds):
                hang = huy_hieu[i] if i < 3 else f"{i+1}."
                text += f"{hang} {ten} — {streak} ngày\n"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Quay lại", callback_data="rank_menu")]
            ])
        )

    elif query.data == "doithe_menu":

        cur.execute(
            "SELECT denomination, COUNT(*) FROM giftcodes WHERE used=0 GROUP BY denomination ORDER BY denomination ASC"
        )
        ds = cur.fetchall()

        if not ds:
            text = "🎫 ĐỔI THẺ CÀO\n\n⚠️ Hiện chưa có mệnh giá thẻ nào khả dụng."
            keyboard = [[InlineKeyboardButton("⬅️ Quay lại", callback_data="home")]]
        else:
            text = "🎫 ĐỔI THẺ CÀO\n\nChọn mệnh giá muốn đổi:"
            keyboard = []
            for menh_gia, so_luong in ds:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{menh_gia:,} VNĐ (còn {so_luong})",
                        callback_data=f"doithe_{menh_gia}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data="home")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("doithe_") and query.data != "doithe_menu":

        menh_gia = int(query.data.split("_")[1])

        cur.execute(
            "SELECT balance FROM users WHERE id=?",
            (user.id,)
        )
        balance = cur.fetchone()[0]

        if balance < menh_gia:
            text = f"""
⚠️ KHÔNG ĐỦ SỐ DƯ

Mệnh giá: {menh_gia:,} VNĐ
Số dư của bạn: {balance:,} VNĐ

Bạn cần thêm {menh_gia - balance:,} VNĐ nữa.
"""
            await query.edit_message_text(text, reply_markup=nut_quay_lai("doithe_menu"))
            return

        cur.execute(
            "SELECT id, code FROM giftcodes WHERE denomination=? AND used=0 LIMIT 1",
            (menh_gia,)
        )
        the = cur.fetchone()

        if the is None:
            text = "⚠️ Rất tiếc, mệnh giá này vừa hết. Vui lòng chọn mệnh giá khác."
            await query.edit_message_text(text, reply_markup=nut_quay_lai("doithe_menu"))
            return

        the_id, ma_the = the

        cur.execute(
            "UPDATE giftcodes SET used=1, used_by=?, used_at=? WHERE id=?",
            (user.id, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), the_id)
        )

        balance_moi = balance - menh_gia
        cur.execute(
            "UPDATE users SET balance=? WHERE id=?",
            (balance_moi, user.id)
        )
        db.commit()

        ghi_lich_su(
            user.id,
            "doi_the",
            -menh_gia,
            f"Đổi thẻ cào mệnh giá {menh_gia:,} VNĐ"
        )

        cur.execute("SELECT referred_by FROM users WHERE id=?", (user.id,))
        gioi_thieu_row = cur.fetchone()

        if gioi_thieu_row and gioi_thieu_row[0]:
            nguoi_gioi_thieu = gioi_thieu_row[0]
            hoa_hong = int(menh_gia * PHAN_TRAM_HOA_HONG / 100)

            if hoa_hong > 0:
                balance_gioi_thieu = cong_tru_tien(nguoi_gioi_thieu, hoa_hong)

                ghi_lich_su(
                    nguoi_gioi_thieu,
                    "hoa_hong",
                    hoa_hong,
                    f"Hoa hồng từ {user.first_name} đổi thẻ"
                )

                try:
                    await context.bot.send_message(
                        chat_id=nguoi_gioi_thieu,
                        text=(
                            f"💸 Bạn nhận được hoa hồng!\n\n"
                            f"👤 Từ: {user.first_name}\n"
                            f"💰 Hoa hồng: +{hoa_hong:,} VNĐ\n"
                            f"💵 Số dư mới: {balance_gioi_thieu:,} VNĐ"
                        )
                    )
                except Exception:
                    pass

        text = f"""
✅ ĐỔI THẺ THÀNH CÔNG!

🎫 Mệnh giá: {menh_gia:,} VNĐ
🔑 Mã thẻ: `{ma_the}`

💰 Số dư còn lại: {balance_moi:,} VNĐ

⚠️ Vui lòng lưu lại mã thẻ, bot sẽ không hiển thị lại.
"""

        await query.edit_message_text(
            text,
            reply_markup=nut_quay_lai(),
            parse_mode="Markdown"
        )

    elif query.data == "danhhieu_menu":

        cur.execute("SELECT danh_hieu FROM users WHERE id=?", (user.id,))
        dang_co = cur.fetchone()[0]

        text = "🎖️ ĐỔI THƯỞNG NỘI BỘ\n\nDùng VNĐ ảo để mua danh hiệu hiển thị trong Hồ sơ:\n\n"

        keyboard = []
        for ten_danh_hieu, gia in DANH_HIEU_SHOP:
            da_so_huu = " ✅" if dang_co == ten_danh_hieu else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{ten_danh_hieu} — {gia:,} VNĐ{da_so_huu}",
                    callback_data=f"muahieu_{gia}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data="home")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("muahieu_"):

        gia_can_mua = int(query.data.split("_")[1])

        ten_danh_hieu = None
        for ten, gia in DANH_HIEU_SHOP:
            if gia == gia_can_mua:
                ten_danh_hieu = ten
                break

        cur.execute("SELECT balance, danh_hieu FROM users WHERE id=?", (user.id,))
        balance, dang_co = cur.fetchone()

        if dang_co == ten_danh_hieu:
            text = f"⚠️ Bạn đang sở hữu danh hiệu {ten_danh_hieu} rồi."
            await query.edit_message_text(text, reply_markup=nut_quay_lai("danhhieu_menu"))
            return

        if balance < gia_can_mua:
            text = f"""
⚠️ KHÔNG ĐỦ SỐ DƯ

Danh hiệu: {ten_danh_hieu}
Giá: {gia_can_mua:,} VNĐ
Số dư của bạn: {balance:,} VNĐ
"""
            await query.edit_message_text(text, reply_markup=nut_quay_lai("danhhieu_menu"))
            return

        balance_moi = balance - gia_can_mua

        cur.execute(
            "UPDATE users SET balance=?, danh_hieu=? WHERE id=?",
            (balance_moi, ten_danh_hieu, user.id)
        )
        db.commit()

        ghi_lich_su(
            user.id,
            "mua_danh_hieu",
            -gia_can_mua,
            f"Mua danh hiệu {ten_danh_hieu}"
        )

        text = f"""
✅ MUA DANH HIỆU THÀNH CÔNG!

🎖️ Danh hiệu mới: {ten_danh_hieu}
💰 Số dư còn lại: {balance_moi:,} VNĐ

✨ Danh hiệu sẽ hiển thị trong mục Hồ sơ.
"""

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "setting":

        cur.execute(
            "SELECT loai, so_tien, mo_ta, thoi_gian FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user.id,)
        )
        ds = cur.fetchall()

        text = "📜 LỊCH SỬ GIAO DỊCH\n\n(10 giao dịch gần nhất)\n\n"

        if not ds:
            text += "Chưa có giao dịch nào."
        else:
            bieu_tuong = {
                "diem_danh": "🎁",
                "doi_the": "🎫",
                "mua_danh_hieu": "🎖️",
                "admin_cong_tien": "➕",
                "admin_tru_tien": "➖",
                "thuong_moi_ban": "👥",
                "hoa_hong": "💸",
                "pvp_thang": "⚔️",
                "pvp_thua": "💀",
            }

            for loai, so_tien, mo_ta, thoi_gian in ds:
                icon = bieu_tuong.get(loai, "🔹")
                dau = "+" if so_tien >= 0 else ""
                text += f"{icon} {mo_ta}\n   {dau}{so_tien:,} VNĐ — {thoi_gian}\n\n"

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "pvp_help":

        bot_username = context.bot.username

        text = f"""
⚔️ PVP CƯỢC TIỀN

Thách đấu người chơi khác, cược tiền, bot random 50/50 - thắng ăn hết!

📝 Cú pháp:
/thachdau <user_id> <số_tiền>

Ví dụ:
/thachdau 123456789 10000

⚠️ Lưu ý:
- Không thể tự thách đấu chính mình
- Cả 2 bên phải đủ tiền cược
- Đối thủ phải /start bot trước
- Gõ lệnh trực tiếp trong khung chat, không bấm nút
"""

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "referral":

        bot_username = context.bot.username
        link_moi = f"https://t.me/{bot_username}?start={user.id}"

        cur.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user.id,))
        so_nguoi_da_moi = cur.fetchone()[0]

        cur.execute(
            "SELECT COALESCE(SUM(so_tien),0) FROM transactions WHERE user_id=? AND loai IN ('thuong_moi_ban','hoa_hong')",
            (user.id,)
        )
        tong_thu_nhap = cur.fetchone()[0]

        text = f"""
👥 MỜI BẠN - NHẬN THƯỞNG

🔗 Link mời của bạn:
{link_moi}

💰 Thưởng ngay: {THUONG_MOI_BAN:,} VNĐ / người mời được
💸 Hoa hồng: {PHAN_TRAM_HOA_HONG}% mỗi lần bạn đó đổi thẻ

📊 Thống kê:
👤 Số người đã mời: {so_nguoi_da_moi}
💵 Tổng thu nhập từ mời bạn: {tong_thu_nhap:,} VNĐ

✨ Gửi link trên cho bạn bè để họ vào bot!
"""

        await query.edit_message_text(text, reply_markup=nut_quay_lai())

    elif query.data == "help":
        await query.edit_message_text(
            "❓ Các lệnh:\n"
            "/start\n"
            "/thachdau <user_id> <số_tiền> — thách đấu PvP",
            reply_markup=nut_quay_lai()
        )

    elif query.data == "home":

        text = f"""
╔══════════════════════╗
🚀 VIP DASHBOARD
╚══════════════════════╝

👋 Xin chào {user.first_name}

🟢 Trạng thái : Online

✨ Chọn chức năng bên dưới.
"""

        await query.edit_message_text(text, reply_markup=menu())

    elif query.data.startswith("cuoc_dongy_"):

        cuoc_id = int(query.data.split("_")[2])

        cur.execute(
            "SELECT nguoi_thach, doi_thu, so_tien, trang_thai FROM cuoc WHERE id=?",
            (cuoc_id,)
        )
        cuoc_data = cur.fetchone()

        if cuoc_data is None:
            await query.edit_message_text("⚠️ Không tìm thấy lời thách đấu này.")
            return

        nguoi_thach, doi_thu, so_tien, trang_thai = cuoc_data

        if user.id != doi_thu:
            await query.answer("⚠️ Đây không phải lời thách đấu gửi cho bạn.", show_alert=True)
            return

        if trang_thai != "cho":
            await query.edit_message_text("⚠️ Lời thách đấu này đã được xử lý trước đó.")
            return

        cur.execute("SELECT balance, name FROM users WHERE id=?", (nguoi_thach,))
        thach_data = cur.fetchone()

        cur.execute("SELECT balance, name FROM users WHERE id=?", (doi_thu,))
        doi_thu_data = cur.fetchone()

        balance_thach, ten_thach = thach_data
        balance_doi_thu, ten_doi_thu = doi_thu_data

        if balance_thach < so_tien or balance_doi_thu < so_tien:
            cur.execute("UPDATE cuoc SET trang_thai='huy' WHERE id=?", (cuoc_id,))
            db.commit()
            await query.edit_message_text(
                "⚠️ Một trong hai bên không còn đủ tiền cược. Trận đấu đã huỷ."
            )
            try:
                await context.bot.send_message(
                    chat_id=nguoi_thach,
                    text="⚠️ Trận thách đấu đã huỷ do không đủ số dư."
                )
            except Exception:
                pass
            return

        nguoi_thang = random.choice([nguoi_thach, doi_thu])
        nguoi_thua = doi_thu if nguoi_thang == nguoi_thach else nguoi_thach

        balance_thang_moi = cong_tru_tien(nguoi_thang, so_tien)
        balance_thua_moi = cong_tru_tien(nguoi_thua, -so_tien)

        cur.execute("UPDATE cuoc SET trang_thai='xong' WHERE id=?", (cuoc_id,))
        db.commit()

        ten_thang = ten_thach if nguoi_thang == nguoi_thach else ten_doi_thu
        ten_thua = ten_doi_thu if nguoi_thang == nguoi_thach else ten_thach

        ghi_lich_su(nguoi_thang, "pvp_thang", so_tien, f"Thắng cược với {ten_thua}")
        ghi_lich_su(nguoi_thua, "pvp_thua", -so_tien, f"Thua cược với {ten_thang}")

        text_ket_qua = f"""
⚔️ KẾT QUẢ TRẬN ĐẤU

🏆 Người thắng: {ten_thang}
💀 Người thua: {ten_thua}

💰 Số tiền cược: {so_tien:,} VNĐ
"""

        await query.edit_message_text(text_ket_qua)

        nguoi_con_lai = nguoi_thach if user.id == doi_thu else doi_thu
        try:
            await context.bot.send_message(chat_id=nguoi_con_lai, text=text_ket_qua)
        except Exception:
            pass

    elif query.data.startswith("cuoc_tuchoi_"):

        cuoc_id = int(query.data.split("_")[2])

        cur.execute(
            "SELECT nguoi_thach, doi_thu, so_tien, trang_thai FROM cuoc WHERE id=?",
            (cuoc_id,)
        )
        cuoc_data = cur.fetchone()

        if cuoc_data is None:
            await query.edit_message_text("⚠️ Không tìm thấy lời thách đấu này.")
            return

        nguoi_thach, doi_thu, so_tien, trang_thai = cuoc_data

        if user.id != doi_thu:
            await query.answer("⚠️ Đây không phải lời thách đấu gửi cho bạn.", show_alert=True)
            return

        if trang_thai != "cho":
            await query.edit_message_text("⚠️ Lời thách đấu này đã được xử lý trước đó.")
            return

        cur.execute("UPDATE cuoc SET trang_thai='tu_choi' WHERE id=?", (cuoc_id,))
        db.commit()

        await query.edit_message_text("❌ Bạn đã từ chối lời thách đấu.")

        try:
            await context.bot.send_message(
                chat_id=nguoi_thach,
                text="❌ Đối thủ đã từ chối lời thách đấu của bạn."
            )
        except Exception:
            pass

# ===========================
# LỆNH ADMIN GỬI THÔNG BÁO THỦ CÔNG
# ===========================

async def gui_thong_bao(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /thongbao <nội dung>")
        return

    noi_dung = " ".join(context.args)

    cur.execute("SELECT id FROM users")
    danh_sach_user = cur.fetchall()

    so_thanh_cong = 0
    so_that_bai = 0

    for (user_id,) in danh_sach_user:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🔔 THÔNG BÁO\n\n{noi_dung}"
            )
            so_thanh_cong += 1
        except Exception:
            so_that_bai += 1

    await update.message.reply_text(
        f"✅ Đã gửi thành công: {so_thanh_cong}\n❌ Thất bại: {so_that_bai}"
    )

# ===========================
# LỆNH ADMIN THÊM THẺ THẬT VÀO KHO
# ===========================

async def them_the(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: /themthe <mệnh_giá> <mã_thẻ>")
        return

    try:
        menh_gia = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Mệnh giá phải là số nguyên, ví dụ: 50000")
        return

    ma_the = context.args[1]

    cur.execute(
        "INSERT INTO giftcodes (denomination, code, used) VALUES (?, ?, 0)",
        (menh_gia, ma_the)
    )
    db.commit()

    await update.message.reply_text(
        f"✅ Đã thêm thẻ vào kho:\n💰 Mệnh giá: {menh_gia:,} VNĐ\n🔑 Mã: {ma_the}"
    )


async def kho_the(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    cur.execute(
        "SELECT denomination, COUNT(*) FROM giftcodes WHERE used=0 GROUP BY denomination ORDER BY denomination ASC"
    )
    ds = cur.fetchall()

    if not ds:
        await update.message.reply_text("📦 Kho thẻ hiện đang trống.")
        return

    text = "📦 KHO THẺ CÒN LẠI\n\n"
    for menh_gia, so_luong in ds:
        text += f"💰 {menh_gia:,} VNĐ — còn {so_luong} thẻ\n"

    await update.message.reply_text(text)

# ===========================
# LỆNH ADMIN XOÁ THẺ TRONG KHO
# ===========================

async def xoa_the(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Cú pháp:\n"
            "/xoathe <mã_thẻ> — xoá 1 mã cụ thể\n"
            "/xoathe menhgia <số> — xoá theo mệnh giá\n"
            "/xoathe all — xoá toàn bộ kho chưa dùng"
        )
        return

    if context.args[0].lower() == "all":
        cur.execute("DELETE FROM giftcodes WHERE used=0")
        so_luong = cur.rowcount
        db.commit()
        await update.message.reply_text(f"🗑️ Đã xoá {so_luong} mã thẻ chưa dùng trong kho.")
        return

    if context.args[0].lower() == "menhgia":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Cú pháp: /xoathe menhgia <số>")
            return
        try:
            menh_gia = int(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Mệnh giá phải là số, ví dụ: 50000")
            return

        cur.execute("DELETE FROM giftcodes WHERE denomination=? AND used=0", (menh_gia,))
        so_luong = cur.rowcount
        db.commit()
        await update.message.reply_text(f"🗑️ Đã xoá {so_luong} mã thẻ mệnh giá {menh_gia:,} VNĐ.")
        return

    ma_the = context.args[0]
    cur.execute("DELETE FROM giftcodes WHERE code=? AND used=0", (ma_the,))
    so_luong = cur.rowcount
    db.commit()

    if so_luong == 0:
        await update.message.reply_text("⚠️ Không tìm thấy mã này trong kho (hoặc đã được dùng nên không thể xoá).")
    else:
        await update.message.reply_text(f"🗑️ Đã xoá mã: {ma_the}")

# ===========================
# LỆNH ADMIN CỘNG/TRỪ TIỀN CHO USER
# ===========================

async def them_tien(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Cú pháp: /themtien <user_id> <số_tiền>\n"
            "Ví dụ: /themtien 123456789 50000\n"
            "Trừ tiền: /themtien 123456789 -20000"
        )
        return

    try:
        target_id = int(context.args[0])
        so_tien = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ user_id và số tiền phải là số nguyên.")
        return

    cur.execute("SELECT balance, name FROM users WHERE id=?", (target_id,))
    ket_qua = cur.fetchone()

    if ket_qua is None:
        await update.message.reply_text("⚠️ Không tìm thấy user này trong database (họ chưa /start bot).")
        return

    balance_cu, ten = ket_qua
    balance_moi = balance_cu + so_tien

    if balance_moi < 0:
        await update.message.reply_text(
            f"⚠️ Không thể thực hiện: số dư sau khi trừ sẽ âm ({balance_moi:,} VNĐ)."
        )
        return

    cur.execute("UPDATE users SET balance=? WHERE id=?", (balance_moi, target_id))
    db.commit()

    hanh_dong = "Cộng" if so_tien >= 0 else "Trừ"

    ghi_lich_su(
        target_id,
        "admin_cong_tien" if so_tien >= 0 else "admin_tru_tien",
        so_tien,
        f"Admin {hanh_dong.lower()} tiền"
    )

    await update.message.reply_text(
        f"✅ {hanh_dong} tiền thành công!\n\n"
        f"👤 User: {ten} ({target_id})\n"
        f"💰 Số dư cũ: {balance_cu:,} VNĐ\n"
        f"{'➕' if so_tien >= 0 else '➖'} Thay đổi: {abs(so_tien):,} VNĐ\n"
        f"💵 Số dư mới: {balance_moi:,} VNĐ"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🔔 Tài khoản của bạn vừa được {'cộng' if so_tien >= 0 else 'trừ'} "
                f"{abs(so_tien):,} VNĐ bởi quản trị viên.\n\n"
                f"💵 Số dư hiện tại: {balance_moi:,} VNĐ"
            )
        )
    except Exception:
        pass

# ===========================
# LỆNH ADMIN KHOÁ TÀI KHOẢN
# ===========================

async def khoa_tai_khoan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cú pháp: /khoa <user_id> [lý do]
    Ví dụ:   /khoa 123456789 spam
    """

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /khoa <user_id> [lý do]")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ user_id phải là số nguyên.")
        return

    ly_do = " ".join(context.args[1:]) if len(context.args) > 1 else "Không nêu lý do"

    cur.execute("SELECT name, bi_khoa FROM users WHERE id=?", (target_id,))
    ket_qua = cur.fetchone()

    if ket_qua is None:
        await update.message.reply_text("⚠️ Không tìm thấy user này trong database.")
        return

    ten, dang_bi_khoa = ket_qua

    if dang_bi_khoa == 1:
        await update.message.reply_text(f"⚠️ {ten} ({target_id}) đã bị khoá từ trước.")
        return

    cur.execute("UPDATE users SET bi_khoa=1 WHERE id=?", (target_id,))
    db.commit()

    await update.message.reply_text(
        f"🔒 Đã khoá tài khoản!\n\n"
        f"👤 User: {ten} ({target_id})\n"
        f"📝 Lý do: {ly_do}"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"⛔ Tài khoản của bạn đã bị khoá.\n\n"
                f"📝 Lý do: {ly_do}\n\n"
                f"Liên hệ quản trị viên nếu bạn cho rằng đây là nhầm lẫn."
            )
        )
    except Exception:
        pass


async def mo_khoa_tai_khoan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cú pháp: /mokhoa <user_id>
    """

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /mokhoa <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ user_id phải là số nguyên.")
        return

    cur.execute("SELECT name, bi_khoa FROM users WHERE id=?", (target_id,))
    ket_qua = cur.fetchone()

    if ket_qua is None:
        await update.message.reply_text("⚠️ Không tìm thấy user này trong database.")
        return

    ten, dang_bi_khoa = ket_qua

    if dang_bi_khoa == 0:
        await update.message.reply_text(f"⚠️ {ten} ({target_id}) hiện không bị khoá.")
        return

    cur.execute("UPDATE users SET bi_khoa=0 WHERE id=?", (target_id,))
    db.commit()

    await update.message.reply_text(
        f"🔓 Đã mở khoá tài khoản!\n\n👤 User: {ten} ({target_id})"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text="🔓 Tài khoản của bạn đã được mở khoá. Bạn có thể sử dụng bot trở lại bằng /start."
        )
    except Exception:
        pass


async def danh_sach_bi_khoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách user đang bị khoá (chỉ admin)"""

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    cur.execute("SELECT id, name FROM users WHERE bi_khoa=1")
    ds = cur.fetchall()

    if not ds:
        await update.message.reply_text("✅ Hiện không có tài khoản nào bị khoá.")
        return

    text = "🔒 DANH SÁCH TÀI KHOẢN BỊ KHOÁ\n\n"
    for uid, ten in ds:
        text += f"👤 {ten} — {uid}\n"

    await update.message.reply_text(text)

# ===========================
# LỆNH ADMIN BACKUP DATABASE
# ===========================

async def backup_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gửi file database.db hiện tại về chat Telegram (chỉ admin)"""

    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền dùng lệnh này.")
        return

    db.commit()  # đảm bảo mọi thay đổi đã ghi xuống ổ đĩa trước khi gửi

    ten_file_backup = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    try:
        shutil.copyfile("database.db", ten_file_backup)

        with open(ten_file_backup, "rb") as f:
            await context.bot.send_document(
                chat_id=user.id,
                document=f,
                filename=ten_file_backup,
                caption=f"💾 Backup database — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )

        await update.message.reply_text("✅ Đã gửi file backup thành công.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Backup thất bại: {e}")

# ===========================
# MAIN
# ===========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("thongbao", gui_thong_bao))
app.add_handler(CommandHandler("themthe", them_the))
app.add_handler(CommandHandler("khothe", kho_the))
app.add_handler(CommandHandler("xoathe", xoa_the))
app.add_handler(CommandHandler("themtien", them_tien))
app.add_handler(CommandHandler("thachdau", thach_dau))
app.add_handler(CommandHandler("khoa", khoa_tai_khoan))
app.add_handler(CommandHandler("mokhoa", mo_khoa_tai_khoan))
app.add_handler(CommandHandler("dsbikhoa", danh_sach_bi_khoa))
app.add_handler(CommandHandler("backup", backup_database))

app.add_handler(
    CallbackQueryHandler(button)
)

print("Bot đang chạy...")

app.run_polling()
