import os
import sys
import subprocess
import json
import time
import threading
from datetime import datetime, timedelta

# ================= অটো ডিপেনডেন্সি ইন্সটলেশন =================
def install_requirements():
    packages = {
        "pyTelegramBotAPI": "telebot",
        "pytz": "pytz",
        "pandas": "pandas",
        "openpyxl": "openpyxl"
    }
    for package, import_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import pytz
import pandas as pd

# ================= কনফিগারেশন =================
BOT_TOKEN = "8678765914:AAFA9KOXyXJEmq88-PS3LAnqQbH51HAzlxc"
ADMIN_ID = 7188760167  # এখানে অ্যাডমিনের টেলিগ্রাম আইডি দিন

bot = telebot.TeleBot(BOT_TOKEN)

os.makedirs("downloads", exist_ok=True)

# ================= ডাটাবেস সেটআপ (JSON) =================
DB_FILE = "bot_data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users":[], "menus": {}, "submissions": {}, "merged_unack": {}, "user_data": {}}
    with open(DB_FILE, "r") as f:
        data = json.load(f)
        if "merged_unack" not in data:
            data["merged_unack"] = {}
        if "user_data" not in data:
            data["user_data"] = {}
        return data

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_db()
user_states = {}

# ================= কীবোর্ড তৈরি করার ফাংশন =================
def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("➕ Add Menu"),
        KeyboardButton("🗑️ Delete Menu"),
        KeyboardButton("👀 View Menu"),
        KeyboardButton("✅ Receive Start")
    )
    markup.add(KeyboardButton("📢 Broadcast"), KeyboardButton("❌ Clear"))
    return markup

def user_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📤 Submit File"))
    markup.add(KeyboardButton("👱 Account"), KeyboardButton("🧑‍💻 Support"))
    return markup

def user_account_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("Add Payment Method"))
    markup.add(KeyboardButton("My Payment Method"))
    markup.add(KeyboardButton("🔙 Back"))
    return markup

def user_submit_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menus = list(db.get("menus", {}).keys())
    if menus:
        buttons =[KeyboardButton(menu) for menu in menus]
        markup.add(*buttons)
    else:
        markup.add(KeyboardButton("কোন মেনু নেই"))
    markup.add(KeyboardButton("🔙 Back"))
    return markup

# ================= /start কমান্ড হ্যান্ডলার =================
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_states[chat_id] = None 
    
    if chat_id == ADMIN_ID:
        bot.send_message(chat_id, "স্বাগতম অ্যাডমিন! প্যানেল থেকে আপনার অপশন সিলেক্ট করুন:", reply_markup=admin_keyboard())
    else:
        if chat_id not in db["users"]:
            db["users"].append(chat_id)
            save_db(db)
        bot.send_message(chat_id, "স্বাগতম! নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি নির্বাচন করুন:", reply_markup=user_main_keyboard())

# ================= অ্যাডমিন মেনু হ্যান্ডলার =================
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.text in["➕ Add Menu", "🗑️ Delete Menu", "👀 View Menu", "✅ Receive Start", "📢 Broadcast", "❌ Clear"])
def admin_actions(message):
    chat_id = message.chat.id
    text = message.text

    if text == "➕ Add Menu":
        user_states[chat_id] = {"state": "adding_menu_name"}
        bot.send_message(chat_id, "নতুন মেনুর নাম লিখে সেন্ড করুন:")
        
    elif text == "✅ Receive Start":
        menus = db.get("menus", {})
        if not menus:
            bot.send_message(chat_id, "বর্তমানে কোন মেনু যুক্ত নেই।")
            return
        
        markup = InlineKeyboardMarkup()
        for m_name in menus.keys():
            markup.add(InlineKeyboardButton(text=f"▶️ {m_name}", callback_data=f"strv_{m_name}"))
        bot.send_message(chat_id, "যে মেনুর ফাইল রিসিভ শুরু করতে চান তা সিলেক্ট করুন:", reply_markup=markup)
        
    elif text == "🗑️ Delete Menu":
        menus = list(db.get("menus", {}).keys())
        if not menus:
            bot.send_message(chat_id, "বর্তমানে কোন মেনু যুক্ত নেই।")
            return
        
        markup = InlineKeyboardMarkup()
        for menu in menus:
            markup.add(InlineKeyboardButton(text=f"❌ {menu}", callback_data=f"delmenu_{menu}"))
        bot.send_message(chat_id, "যে মেনুটি ডিলিট করতে চান তার উপর ক্লিক করুন:", reply_markup=markup)
        
    elif text == "👀 View Menu":
        menus = db.get("menus", {})
        if not menus:
            bot.send_message(chat_id, "বর্তমানে কোন মেনু যুক্ত নেই।")
        else:
            menu_list = ""
            for i, (m_name, m_data) in enumerate(menus.items()):
                status = m_data.get('deadline_str', 'Not Started')
                menu_list += f"{i+1}. {m_name} (End: {status})\n"
            bot.send_message(chat_id, f"<b>বর্তমান মেনুসমূহ:</b>\n{menu_list}", parse_mode="HTML")
            
    elif text == "📢 Broadcast":
        user_states[chat_id] = {"state": "broadcasting"}
        bot.send_message(chat_id, "আপনার বার্তাটি লিখুন (টেক্সট, ছবি বা ফাইলও সেন্ড করতে পারেন):")
        
    elif text == "❌ Clear":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Yes, Clear Chat", callback_data="clear_yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="clear_no")
        )
        bot.send_message(chat_id, "আপনি কি নিশ্চিত যে আপনি চ্যাটের মেসেজগুলো ক্লিয়ার করতে চান?", reply_markup=markup)

# ================= অ্যাডমিন স্টেট ইনপুট হ্যান্ডলার =================
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and (user_states.get(msg.chat.id) or {}).get("state") in["adding_menu_name", "adding_menu_time", "broadcasting"], content_types=['text', 'photo', 'document', 'video'])
def admin_state_processor(message):
    chat_id = message.chat.id
    state_info = user_states.get(chat_id) or {}
    state = state_info.get("state")
    
    if state == "adding_menu_name":
        if message.content_type != 'text':
            bot.send_message(chat_id, "দয়া করে শুধুমাত্র টেক্সট দিন।")
            return
            
        menu_name = message.text
        if menu_name in db.get("menus", {}):
            bot.send_message(chat_id, "এই মেনুটি আগে থেকেই আছে!")
        else:
            db["menus"][menu_name] = {"deadline_ts": 0, "deadline_str": "Not Started"}
            if "submissions" not in db:
                db["submissions"] = {}
            if menu_name not in db["submissions"]:
                db["submissions"][menu_name] = {"subs": {}}
            save_db(db)
            bot.send_message(chat_id, f"✅ মেনু '{menu_name}' সফলভাবে যুক্ত হয়েছে।\n(নোট: 'Receive Start' অপশন থেকে টাইম সেট না করা পর্যন্ত ইউজাররা এই মেনুতে ফাইল দিতে পারবে বোমা।)", reply_markup=admin_keyboard())
        user_states[chat_id] = None
            
    elif state == "adding_menu_time":
        time_str = message.text.strip()
        try:
            dt_time = datetime.strptime(time_str, "%I:%M %p").time()
            now = datetime.now(pytz.timezone('Asia/Dhaka'))
            deadline_dt = datetime.combine(now.date(), dt_time)
            deadline_dt = pytz.timezone('Asia/Dhaka').localize(deadline_dt)
            
            if deadline_dt < now:
                deadline_dt += timedelta(days=1)
                
            menu_name = state_info["menu_name"]
            
            db["menus"][menu_name]["deadline_ts"] = deadline_dt.timestamp()
            db["menus"][menu_name]["deadline_str"] = deadline_dt.strftime('%d-%b-%Y %I:%M %p')
            
            if "submissions" not in db:
                db["submissions"] = {}
            if menu_name not in db["submissions"]:
                db["submissions"][menu_name] = {"subs": {}}
                
            save_db(db)
            
            bot.send_message(chat_id, f"✅ মেনু '{menu_name}' এর ফাইল জমা নেওয়া শুরু হয়েছে।\n⏰ লাস্ট টাইম: {deadline_dt.strftime('%I:%M %p')}", reply_markup=admin_keyboard())
            user_states[chat_id] = None
            
        except ValueError:
            bot.send_message(chat_id, "⚠️ সময়ের ফরম্যাট ভুল হয়েছে। দয়া করে 10:00 PM বা 05:30 AM এই ফরম্যাটে লিখুন:")
        
    elif state == "broadcasting":
        users = db.get("users",[])
        success = 0
        bot.send_message(chat_id, f"📢 ব্রডকাস্ট শুরু হচ্ছে... মোট ইউজার: {len(users)}")
        
        for user in users:
            if user != ADMIN_ID:
                try:
                    bot.copy_message(user, chat_id, message.message_id)
                    success += 1
                except Exception:
                    pass
        bot.send_message(chat_id, f"✅ ব্রডকাস্ট সম্পন্ন হয়েছে! পাঠানো হয়েছে {success} জন ইউজারকে।")
        user_states[chat_id] = None

# ================= ইউজার স্ট্যাটিক মেনু হ্যান্ডলার =================
@bot.message_handler(func=lambda msg: msg.chat.id != ADMIN_ID and msg.text in["📤 Submit File", "👱 Account", "🧑‍💻 Support", "🔙 Back", "Add Payment Method", "My Payment Method"])
def user_static_menu(message):
    chat_id = message.chat.id
    text = message.text
    user_states[chat_id] = None 
    
    if text == "📤 Submit File":
        bot.send_message(chat_id, "❓ ক্যাটাগরি সিলেক্ট করুন:", reply_markup=user_submit_keyboard())
        
    elif text == "👱 Account":
        bot.send_message(chat_id, "👱 অ্যাকাউন্ট অপশন:", reply_markup=user_account_keyboard())
        
    elif text == "🧑‍💻 Support":
        bot.send_message(chat_id, f"কিভাবে ফাইল সাবমিট করতে হয়?\n👉 <a href='https://t.me/active_squad_backup/3'>Video</a>\n অ্যাডমিনের সাথে সরাসরি যোগাযোগ করতে নিচের লিংকে ক্লিক করুন:\n👉 <a href='tg://user?id={ADMIN_ID}'>Admin Contact</a>", parse_mode="HTML")
        
    elif text == "🔙 Back":
        bot.send_message(chat_id, "মেইন মেনু:", reply_markup=user_main_keyboard())
        
    elif text == "Add Payment Method":
        user_states[chat_id] = {"state": "adding_payment_name"}
        bot.send_message(chat_id, "আপনি কিসের মাধ্যমে পেমেন্ট নিতে চান?")
        
    elif text == "My Payment Method":
        uid = str(chat_id)
        u_data = db.get("user_data", {}).get(uid, {})
        if u_data:
            bot.send_message(chat_id, f"💳 <b>আপনার পেমেন্ট মেথড:</b>\n\n<b>মাধ্যম:</b> {u_data.get('method')}\n<b>নাম্বার:</b> <code>{u_data.get('number')}</code>", parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ আপনি এখনো কোনো পেমেন্ট মেথড সেট করেননি।")

# ================= ইউজার পেমেন্ট মেথড সেটআপ হ্যান্ডলার =================
@bot.message_handler(func=lambda msg: msg.chat.id != ADMIN_ID and (user_states.get(msg.chat.id) or {}).get("state") in["adding_payment_name", "adding_payment_number"], content_types=['text'])
def user_payment_setup(message):
    chat_id = message.chat.id
    state_info = user_states.get(chat_id) or {}
    state = state_info.get("state")
    
    if state == "adding_payment_name":
        method_name = message.text
        user_states[chat_id] = {"state": "adding_payment_number", "method": method_name}
        bot.send_message(chat_id, f"আপনার {method_name} নাম্বার দিন")
        
    elif state == "adding_payment_number":
        method_number = message.text
        method_name = state_info.get("method")
        
        uid = str(chat_id)
        if "user_data" not in db:
            db["user_data"] = {}
        
        db["user_data"][uid] = {"method": method_name, "number": method_number}
        save_db(db)
        
        bot.send_message(chat_id, f"✅ আপনার {method_name} পেমেন্ট মেথড সফলভাবে যুক্ত হয়েছে!", reply_markup=user_account_keyboard())
        user_states[chat_id] = None

# ================= ইউজার ডাইনামিক মেনু ক্লিক (সাবমিট ফাইল) =================
@bot.message_handler(func=lambda msg: msg.chat.id != ADMIN_ID and msg.text in db.get("menus", {}))
def user_menu_clicked(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    menu_name = message.text
    
    uid_str = str(user_id)
    if uid_str not in db.get("user_data", {}):
        bot.send_message(chat_id, "আগে আপনার পেমেন্ট সিস্টেম যুক্ত করুন তারপর ফাইল সাবমিট করুন। পেমেন্ট সিস্টেম যুক্ত করতে Account এ যান।")
        return

    menu_info = db["menus"][menu_name]
    
    if menu_info.get("deadline_ts", 0) == 0:
        bot.send_message(chat_id, f"এখনো {menu_name} আয়ডি জমা নেওয়া শুরু হয়নি।")
        return

    now_ts = datetime.now(pytz.timezone('Asia/Dhaka')).timestamp()
    if now_ts > menu_info["deadline_ts"]:
        bot.send_message(chat_id, "এই মেনুর ফাইল সাবমিট করার সময় শেষ হয়ে গেছে।")
        return

    user_states[chat_id] = {"state": "waiting_for_file", "menu": menu_name}
    bot.send_message(chat_id, "📂 আপনার xlsx ফাইলটি সেন্ড করুন:")

# ================= ফাইল (Document) রিসিভ হ্যান্ডলার =================
@bot.message_handler(content_types=['document'], func=lambda msg: msg.chat.id != ADMIN_ID)
def handle_docs(message):
    chat_id = message.chat.id
    state_info = user_states.get(chat_id) or {}
    
    if state_info.get("state") == "waiting_for_file":
        menu_name = state_info.get("menu")
        file_name = message.document.file_name
        
        if not file_name.endswith('.xlsx'):
            bot.send_message(chat_id, "📂 দয়া করে শুধুমাত্র .xlsx ফাইল সেন্ড করুন।")
            return
            
        bot.send_message(chat_id, "📂 ফাইল প্রোসেস করা হচ্ছে, অপেক্ষা করুন...")
        
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            filepath = f"downloads/{chat_id}_{int(time.time())}.xlsx"
            with open(filepath, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            df = pd.read_excel(filepath, header=None)
            total_id = len(df)
            duplicate_id = df.duplicated().sum()
            
            user_id = message.from_user.id
            sub_id = f"{int(time.time() * 1000)}_{user_id}"
            
            if menu_name not in db["submissions"]:
                db["submissions"][menu_name] = {"subs": {}}
                
            db["submissions"][menu_name]["subs"][sub_id] = {
                "file": filepath,
                "user_id": user_id,
                "msg_id": message.message_id,
                "ack": False,
                "rej_ack": False,
                "pay_ack": False,
                "merged": False
            }
            save_db(db)
            
            tz = pytz.timezone('Asia/Dhaka')
            bd_time = datetime.now(tz).strftime('%Y-%m-%d %I:%M:%S %p')
            
            name = message.from_user.first_name
            if message.from_user.last_name:
                name += f" {message.from_user.last_name}"
            username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
            
            uid_str = str(user_id)
            u_data = db.get("user_data", {}).get(uid_str, {})
            payment_info = f"{u_data.get('method')} - {u_data.get('number')}" if u_data else "Not Set"
            
            caption = f"📁 <b>New File Received</b>\n\n" \
                      f"<b>Total ID:</b> {total_id}\n" \
                      f"<b>Duplicate ID:</b> {duplicate_id}\n\n" \
                      f"⚙️ <b>Service:</b> {menu_name}\n" \
                      f"💳 <b>Payment:</b> {payment_info}\n" \
                      f"👤 <b>Name:</b> {name}\n" \
                      f"🔗 <b>UserName:</b> {username}\n" \
                      f"🆔 <b>ID:</b> <code>{user_id}</code>\n" \
                      f"⏰ <b>Time:</b> {bd_time}\n" \
                      f"📄 <b>File:</b> {file_name}"
            
            markup = InlineKeyboardMarkup()
            # প্রথম সারিতে Received এবং Reject বাটন
            markup.row(
                InlineKeyboardButton(text="✅ Received", callback_data=f"recv_{sub_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{sub_id}")
            )
            # দ্বিতীয় সারিতে Payment Done বাটন
            markup.row(InlineKeyboardButton(text="💸 Payment Done", callback_data=f"pay_{sub_id}"))
            
            with open(filepath, 'rb') as doc:
                bot.send_document(ADMIN_ID, doc, caption=caption, parse_mode="HTML", reply_markup=markup)
            
            bot.send_message(chat_id, "✅ আপনার ফাইলটি সফলভাবে অ্যাডমিনের কাছে পাঠানো হয়েছে।", reply_markup=user_main_keyboard())
            user_states[chat_id] = None 
            
        except Exception as e:
            bot.send_message(chat_id, "⚠️ আপনার ফাইলটি রিড করা সম্ভব হয়নি। ফাইলটি সঠিক কিনা যাচাই করুন।")

# ================= ইনলাইন বাটন (Callback Query) হ্যান্ডলার =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("strv_"):
        menu_name = call.data.split("_", 1)[1]
        user_states[call.message.chat.id] = {"state": "adding_menu_time", "menu_name": menu_name}
        bot.send_message(call.message.chat.id, f"'{menu_name}' এর জন্য ফাইল রিসিভ করার শেষ সময় দিন (যেমন: 10:00 PM বা 05:30 AM):")
        bot.answer_callback_query(call.id)
        
    elif call.data.startswith("delmenu_"):
        menu_name = call.data.split("_", 1)[1]
        menus = db["menus"]
        if menu_name in menus:
            del db["menus"][menu_name]
            save_db(db)
            bot.answer_callback_query(call.id, f"'{menu_name}' ডিলিট করা হয়েছে!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, f"'{menu_name}' মেনুটি মুছে ফেলা হয়েছে।", reply_markup=admin_keyboard())
            
    # Received, Reject এবং Payment Done বাটন লজিক
    elif call.data.startswith("recv_") or call.data.startswith("pay_") or call.data.startswith("rej_"):
        action, sub_id = call.data.split("_", 1)
        found = False
        user_id = None
        msg_id = None
        current_sub_data = None
        
        for m_name, m_data in db.get("submissions", {}).items():
            if "subs" in m_data and sub_id in m_data["subs"]:
                current_sub_data = m_data["subs"][sub_id]
                found = True
                
                if action == "recv" and not current_sub_data.get("ack", False):
                    current_sub_data["ack"] = True
                    user_id = current_sub_data["user_id"]
                    msg_id = current_sub_data.get("msg_id")
                    
                elif action == "pay" and not current_sub_data.get("pay_ack", False):
                    current_sub_data["pay_ack"] = True
                    user_id = current_sub_data["user_id"]
                    msg_id = current_sub_data.get("msg_id")
                    
                elif action == "rej" and not current_sub_data.get("rej_ack", False):
                    current_sub_data["rej_ack"] = True
                    user_id = current_sub_data["user_id"]
                    msg_id = current_sub_data.get("msg_id")
                
                # যদি Reject করা হয় অথবা (Received ও Payment Done) উভয়ই করা হয়ে যায়, তবে ডেটা ডিলিট করে দেবে
                if current_sub_data.get("rej_ack", False) or (current_sub_data.get("ack", False) and current_sub_data.get("pay_ack", False)):
                    filepath = current_sub_data.get("file")
                    if filepath and os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
                    del m_data["subs"][sub_id]
                    current_sub_data = None # ক্লিয়ার করা হলো যাতে বাটন আর রেন্ডার না হয়

                save_db(db)
                break
                
        if user_id:
            try:
                if action == "recv":
                    text = "✅ আপনার ফাইলটি Received করা হয়েছে।"
                elif action == "pay":
                    text = "✅ আপনার পেমেন্ট সম্পন্ন হয়েছে।"
                elif action == "rej":
                    text = "❌ আপনার ফাইলটি Rejecte করা হয়েছে"

                bot.send_message(user_id, text, reply_to_message_id=msg_id)
                bot.answer_callback_query(call.id, "ইউজারকে নোটিফিকেশন পাঠানো হয়েছে!")
                
                markup = InlineKeyboardMarkup()
                if current_sub_data:
                    row1 =[]
                    if not current_sub_data.get("ack", False):
                        row1.append(InlineKeyboardButton(text="✅ Received", callback_data=f"recv_{sub_id}"))
                    if not current_sub_data.get("rej_ack", False):
                        row1.append(InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{sub_id}"))
                        
                    if row1:
                        markup.row(*row1)
                        
                    if not current_sub_data.get("pay_ack", False):
                        markup.row(InlineKeyboardButton(text="💸 Payment Done", callback_data=f"pay_{sub_id}"))
                
                if markup.keyboard:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
                else:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                    
                admin_text = f"✅ User {user_id} কে {'Received' if action=='recv' else 'Payment Done' if action=='pay' else 'Reject'} মেসেজ পাঠানো হয়েছে।"
                bot.send_message(ADMIN_ID, admin_text, reply_to_message_id=call.message.message_id)
                
            except Exception:
                bot.answer_callback_query(call.id, "ইউজারকে মেসেজ পাঠানো সম্ভব হয়নি!", show_alert=True)
        elif found:
            bot.answer_callback_query(call.id, "এটি ইতিমধ্যে সম্পন্ন হয়েছে।", show_alert=True)
            markup = InlineKeyboardMarkup()
            if current_sub_data:
                row1 =[]
                if not current_sub_data.get("ack", False):
                    row1.append(InlineKeyboardButton(text="✅ Received", callback_data=f"recv_{sub_id}"))
                if not current_sub_data.get("rej_ack", False):
                    row1.append(InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{sub_id}"))
                    
                if row1:
                    markup.row(*row1)
                    
                if not current_sub_data.get("pay_ack", False):
                    markup.row(InlineKeyboardButton(text="💸 Payment Done", callback_data=f"pay_{sub_id}"))
                
            if markup.keyboard:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
            else:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        else:
            bot.answer_callback_query(call.id, "এই ডেটা আর ডাটাবেসে নেই বা সম্পূর্ণ প্রসেস শেষ হয়ে মুছে গেছে।", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    elif call.data.startswith("recvall_"):
        merge_id = call.data.split("_", 1)[1]
        unack_details = db.get("merged_unack", {}).get(merge_id,[])
        
        if unack_details:
            success = 0
            for info in unack_details:
                try:
                    bot.send_message(info["user_id"], "✅ আপনার ফাইলটি Received করা হয়েছে。", reply_to_message_id=info.get("msg_id"))
                    success += 1
                except Exception:
                    pass
                
                sub_id = info.get("sub_id")
                if sub_id:
                    for m_name, m_data in db.get("submissions", {}).items():
                        if "subs" in m_data and sub_id in m_data["subs"]:
                            m_data["subs"][sub_id]["ack"] = True
                            
                            # যদি Payment Done আগে থেকে হয়ে থাকে, তবে ডেটা ও ফাইল ডিলিট করে দেওয়া
                            if m_data["subs"][sub_id].get("pay_ack", False):
                                filepath = m_data["subs"][sub_id].get("file")
                                if filepath and os.path.exists(filepath):
                                    try:
                                        os.remove(filepath)
                                    except:
                                        pass
                                del m_data["subs"][sub_id]
                            break
                            
            del db["merged_unack"][merge_id]
            save_db(db)
            
            bot.answer_callback_query(call.id, f"{success} জন ইউজারকে নোটিফিকেশন পাঠানো হয়েছে!")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(ADMIN_ID, f"✅ {success} জন ইউজারকে একযোগে Received মেসেজ পাঠানো হয়েছে।", reply_to_message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "সকলকে ইতিমধ্যে মেসেজ পাঠানো হয়েছে বা ডাটা পাওয়া যায়নি!", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    elif call.data == "clear_yes":
        bot.answer_callback_query(call.id, "চ্যাট ক্লিয়ার করা হচ্ছে...")
        chat_id = call.message.chat.id
        current_msg_id = call.message.message_id
        
        for msg_id in range(current_msg_id, max(0, current_msg_id - 100), -1):
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
                
        bot.send_message(chat_id, "✅ আপনার চ্যাট হিস্টোরি ক্লিয়ার করা হয়েছে।", reply_markup=admin_keyboard())
        
    elif call.data == "clear_no":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ================= অটোমেটিক 10 দিনের পুরোনো ডেটা ক্লিয়ার করার ফাংশন =================
def clean_old_data_and_files():
    now_ts = time.time()
    ten_days_sec = 10 * 24 * 60 * 60
    
    if "submissions" in db:
        for menu_name, menu_data in db["submissions"].items():
            if "subs" in menu_data:
                to_delete =[]
                for sub_id, sub_data in menu_data["subs"].items():
                    try:
                        sub_ts = int(sub_id.split('_')[0]) / 1000
                        if now_ts - sub_ts > ten_days_sec:
                            to_delete.append(sub_id)
                    except:
                        pass
                for sub_id in to_delete:
                    filepath = menu_data["subs"][sub_id].get("file")
                    if filepath and os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
                    del menu_data["subs"][sub_id]
    save_db(db)
    
    for filename in os.listdir("downloads"):
        filepath = os.path.join("downloads", filename)
        if os.path.isfile(filepath):
            try:
                if os.stat(filepath).st_mtime < now_ts - ten_days_sec:
                    os.remove(filepath)
            except:
                pass

# ================= ব্যাকগ্রাউন্ড প্রসেস (ডেডলাইন চেক ও ফাইল মার্জ) =================
def process_merged_files(menu_name):
    subs_data = db.get("submissions", {}).get(menu_name, {})
    dfs =[]
    valid_files = 0
    unack_details =[]
    
    if isinstance(subs_data, dict) and "subs" in subs_data:
        subs = subs_data["subs"]
        for sub_id, sub_data in subs.items():
            if sub_data.get("merged", False):
                continue
            
            sub_data["merged"] = True
            
            # যদি ফাইলটি রিজেক্ট না করা হয়ে থাকে, শুধুমাত্র তবেই Received All এ লিস্ট হবে
            if not sub_data.get("ack", False) and not sub_data.get("rej_ack", False):
                unack_details.append({
                    "user_id": sub_data["user_id"],
                    "msg_id": sub_data.get("msg_id"),
                    "sub_id": sub_id
                })
            
            if os.path.exists(sub_data["file"]):
                try:
                    df = pd.read_excel(sub_data["file"], header=None)
                    dfs.append(df)
                    valid_files += 1
                except:
                    pass
                    
    if dfs:
        merged_df = pd.concat(dfs, ignore_index=True)
        total_id = len(merged_df)
        total_dup = merged_df.duplicated().sum()
        
        merged_filepath = f"downloads/Merged_{menu_name}_{int(time.time())}.xlsx"
        merged_df.to_excel(merged_filepath, index=False, header=False)
        
        caption = f"Total File: {valid_files}\n" \
                  f"Total ID: {total_id}\n" \
                  f"Total Duplicate: {total_dup}"
        
        markup = None
        if unack_details:
            merge_id = f"merge_{int(time.time())}"
            if "merged_unack" not in db:
                db["merged_unack"] = {}
            db["merged_unack"][merge_id] = unack_details
            save_db(db)
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="✅ Received All", callback_data=f"recvall_{merge_id}"))
        
        bot.send_message(ADMIN_ID, f"✅ <b>'{menu_name}'</b> এর সময় শেষ হয়েছে! আজকের ডাটা একীভূত করে নিচে দেওয়া হলো:", parse_mode="HTML")
        with open(merged_filepath, 'rb') as doc:
            bot.send_document(ADMIN_ID, doc, caption=caption, reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, f"⚠️ '{menu_name}' এর সময় শেষ হয়েছে, কিন্তু আজকে নতুন কোনো ফাইল জমা পড়েনি।")

def deadline_checker():
    last_cleanup = 0
    while True:
        try:
            now_ts = datetime.now(pytz.timezone('Asia/Dhaka')).timestamp()
            
            if time.time() - last_cleanup > 3600:
                clean_old_data_and_files()
                last_cleanup = time.time()
                
            menus = db.get("menus", {})
            expired_menus =[]
            
            for menu_name, menu_info in menus.items():
                if menu_info.get("deadline_ts", 0) != 0 and now_ts >= menu_info["deadline_ts"]:
                    expired_menus.append(menu_name)
            
            for menu_name in expired_menus:
                process_merged_files(menu_name)
                db["menus"][menu_name]["deadline_ts"] = 0
                db["menus"][menu_name]["deadline_str"] = "Not Started"
                save_db(db)
                
        except Exception as e:
            print(f"Error in deadline checker: {e}")
            
        time.sleep(30)

threading.Thread(target=deadline_checker, daemon=True).start()

# ================= বট রান করা =================
print("Bot is running...")
bot.infinity_polling()
