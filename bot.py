import os
import sys
import subprocess
import asyncio
import logging
import json
import time
import pyotp
import httpx
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import firebase_admin
from firebase_admin import credentials, db

# --- Auto-install Dependencies ---
def install_dependencies():
    packages = ["aiogram", "firebase-admin", "httpx", "pyotp"]
    for package in packages:
        try:
            if package == "firebase-admin":
                import firebase_admin
            else:
                __import__(package)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_dependencies()

# --- Configuration ---
API_TOKEN = "8871803888:AAEOV3_UI1_7dEc4oFhwA2mgY2bkN8cO84Y"
ADMIN_ID = 7188760167
SMS_BOWER_API_KEY = "88J8QPh2vPkrzJZuP7GS6Xh8OfTdWzCJ"
SMS_BOWER_USER_ID = "493707"

# --- Constants & Mappings ---
SERVICE_MAPPING = {
    'fb': '📘 Facebook', 'tg': '✈️ Telegram', 'go': '🇬 Google', 'wa': '💬 WhatsApp', 
    'ig': '📸 Instagram', 'vi': '🟣 Viber', 'tw': '🐦 Twitter/X', 'nf': '🍿 Netflix', 
    'am': '🛒 Amazon', 'ds': '🎮 Discord', 'tl': '📱 Telegram', 'vk': '🟦 VKontakte',
    'ok': '🟧 Odnoklassniki', 'mm': '🟩 Microsoft', 'apple': '🍏 Apple', 'uber': '🚗 Uber'
}

COUNTRY_FLAGS = {
    '0': '🇷🇺', '1': '🇺🇦', '2': '🇰🇿', '3': '🇨🇳', '4': '🇵🇭', '5': '🇲🇲', '6': '🇮🇩', '7': '🇲🇾', '8': '🇰🇪', 
    '9': '🇹🇿', '10': '🇻🇳', '11': '🇰🇬', '12': '🇺🇸', '13': '🇮🇱', '14': '🇭🇰', '15': '🇵🇱', '16': '🇬🇧', 
    '17': '🇲🇬', '18': '🇨🇬', '19': '🇳🇬', '20': '🇲🇴', '21': '🇪🇬', '22': '🇮🇳', '23': '🇮🇪', '24': '🇰🇭', 
    '25': '🇱🇦', '26': '🇭🇹', '27': '🇨🇮', '28': '🇬🇲', '29': '🇷🇸', '30': '🇾🇪', '31': '🇿🇦', '32': '🇷🇴', 
    '33': '🇨🇴', '34': '🇪🇪', '35': '🇦🇿', '36': '🇨🇦', '37': '🇲🇦', '38': '🇬🇭', '39': '🇦🇷', '40': '🇺🇿', 
    '41': '🇨🇲', '42': '🇹🇩', '43': '🇩🇪', '44': '🇱🇹', '45': '🇭🇷', '46': '🇸🇪', '47': '🇮🇶', '48': '🇳🇱', 
    '49': '🇱🇻', '50': '🇦🇹', '51': '🇧🇾', '52': '🇹🇭', '53': '🇸🇦', '54': '🇲🇽', '55': '🇹🇼', '56': '🇪🇸', 
    '57': '🇮🇷', '58': '🇩🇿', '59': '🇸🇮', '60': '🇧🇩', '61': '🇸🇳', '62': '🇹🇷', '63': '🇨🇿', '64': '🇱🇰', 
    '65': '🇵🇪', '66': '🇵🇰', '67': '🇳🇿', '68': '🇬🇳', '69': '🇲🇱', '70': '🇻🇪', '71': '🇪🇹', '72': '🇲🇳', 
    '73': '🇧🇷', '74': '🇦🇫', '75': '🇺🇬', '76': '🇦🇴', '77': '🇨🇾', '78': '🇫🇷', '79': '🇵🇬', '80': '🇲🇿', 
    '81': '🇳🇵', '82': '🇧🇪', '83': '🇧🇬', '84': '🇭🇺', '85': '🇲🇩', '86': '🇮🇹', '87': '🇵🇾', '88': '🇭🇳', 
    '89': '🇹🇳', '90': '🇳🇮', '91': '🇹🇱', '92': '🇧🇴', '93': '🇨🇷', '94': '🇬🇹', '95': '🇦🇪', '96': '🇿🇼', 
    '97': '🇵🇷', '98': '🇸🇩', '99': '🇹🇬', '100': '🇰🇼', '101': '🇸🇻', '102': '🇱🇾', '103': '🇯🇲', '104': '🇹🇹', 
    '105': '🇪🇨', '106': '🇸🇿', '107': '🇴🇲', '108': '🇧🇦', '109': '🇩🇴', '110': '🇸🇾', '111': '🇶🇦', '112': '🇵🇦', 
    '113': '🇨🇺', '114': '🇲🇷', '115': '🇸🇱', '116': '🇯🇴', '117': '🇵🇹', '118': '🇸🇳', '119': '🇷🇼', '120': '🇨🇬',
    '121': '🇬🇶', '122': '🇲🇱', '123': '🇦🇩', '124': '🇱🇷', '125': '🇧🇿', '126': '🇲🇦', '127': '🇲🇺', '128': '🇸🇴',
    '129': '🇦🇴', '130': '🇹🇩', '131': '🇨🇻', '132': '🇧🇮', '133': '🇬🇦', '134': '🇨🇫', '135': '🇭🇹', '136': '🇧🇿',
    '137': '🇻🇺', '138': '🇸🇷', '139': '🇬🇾', '140': '🇧🇯', '141': '🇧🇳', '142': '🇬🇼', '143': '🇲🇬', '144': '🇨🇲',
    '145': '🇹🇬', '146': '🇳🇪', '147': '🇿🇲', '148': '🇲🇱', '149': '🇪🇷', '150': '🇱🇸'
}

def get_service_name(code):
    return SERVICE_MAPPING.get(code.lower(), f"🔹 {code.upper()}")

def get_country_flag(code):
    return COUNTRY_FLAGS.get(str(code), '🌍')

# Firebase Service Account
FIREBASE_CONFIG = {
  "type": "service_account",
  "project_id": "number-bot-9a5bd",
  "private_key_id": "677dc5cbae779ddd257042a9ae50e525eede63c0",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCYLmbso+CUiy4F\namrYebloYYsdbesO6KAF2QqaFeYTMnd0ddIhoIA8uGDgnHvoNDCAzgJ9nOv1l0YY\nnYY2zNwpoF+fXiPfKw6SxZfkG5Ig7r3jeAAV3XsTdn3SxIrmWXatWiox2ovnPX+C\n4ks208sMllOlCZn3gaYhg2jtxZS69iokZkJoaJhbpfEf2HLJ1511qKeebQV4t/2q\nzWr7cQg1qK6cYKZIJiHdXMnYRf+NLesgt8R7BCL93KmCCJX+Gymzq8woBIq0Mrlf\n8Fq1KSpvWjDeKCm/MFl7/8MHeRG8QjFN/HG8SHhGNzQlHyXQ3r3pRe43JI+y7/4W\ndeZ1OqIBAgMBAAECggEADe5lhrFD3GVXW7CPwmx2QCt50EJhO9ao25Awa8Wob8Z1\ncAhfKavnQWfBmp5Iq4uniwsQ6E3mve9Qv+0fvcGIQBlJ162HDCWFaoNDMeMiP/iL\nEplILLg/TZtRzmsmqgqzlhAEf9bZatxS4Xj02LqPwoG6e4fC/Aj22+eLQgUN5gWB\n1IgpVVQHYKD761qwo4/+hHl6EPuktunVwbEBMnVulYjX6NAWUHKlldFtCeyBC9fZ\n0PWZhN4D79/YvYjCgaQDGBUkKRdc4xX+OFgYJ1eYbpnO0O4XlJxDot3mF8fep/pY\ndGQ6t62ssEgu9OXuRLGRL6h9W1bLQ0tWq2E4l5R+nwKBgQDKqM2eqVUs8aTVxu9a\ndAcqbRBne1oQ+CwDcez/aqIVjjGLIZSMngmI+6hK0UcQkHwXDD8ckZhkqdAzp5G2\nglEqKDSecaUxZAnrSlet198WO2Ts6wD++XmKw1aURk/vvnHSg/SSduqL4xbdoQ8s\nco58ZMIw/Zdf4aLLoEfy/K7ytwKBgQDAPGFzknhTbTtZgN3UleC+93EI7GePzEjJ\nMWXwp9hE/N94PMa359CDyGE7OxKw7gU97nohAuS+RN4Hv3m1dScuEpeTg3y6bsfH\n/U25oCHfMrtSo7nuTMsWMDipuPLAlPOpUu4ooADHq9z5CxNm5cbywpefcsQObKNf\nBXiEupL5BwKBgH1LG8UKH9TnmOdqVLTxozSBtXCk/KwdIukGWGYZQRhejxbbrgG5\n+18rZ4LKHEuLaIy/T42UHkmuC0DESvwxWYjczpte26jLlq5Xihm6qvwNwHoRWM5K\n4u/9kNufFPC+J5TlbCHZT20o+wwO9VifgqQ5jy3Guv3WfFW0RIdf3bHFAoGBALkp\n79w4mzoQnvgpToL0EtUe1nv36hDyfrF8qWpS4dghksboE6kU2x30puM8lVZjDh2H\nVY/yj45OG2dvIbaNL74LHoFyR3P0PO7/qBxCiB3Lae/B0NgelAe9Tvb8NKcXUlQo\nk0oCRH4Ppvsjlf6pGSbAFPf6van/LqXaSSnf5K2FAoGAbn8eIez3Mf01Kd7NWuzw\n7tjEEocwT9Dal0X+ysJ+5saZ+L03G24HSFq4ORXgYLWdt4jHYM8VJ7472M/CVuWY\nHDdnfaWjWEwucoKtHUi5fUgj0F5oPh3rg3DrEe0og5xmzPZuOyJtnFmsQY93PC1U\nMeDGZz6npeo09mp17pxffxU=\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@number-bot-9a5bd.iam.gserviceaccount.com",
  "client_id": "115514004749804990702",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40number-bot-9a5bd.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CONFIG)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://number-bot-9a5bd-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

# --- States ---
class BotStates(StatesGroup):
    selecting_service = State()
    selecting_country = State()
    depositing_amount = State()
    entering_txid = State()
    entering_2fa_key = State()
    admin_adding_service = State()
    admin_deleting_service = State()
    admin_adding_country = State()
    admin_adding_country_details = State()
    admin_deleting_country = State()
    admin_setting_dollar_rate = State()
    admin_setting_country_rate_srv = State()
    admin_setting_country_rate_country = State()
    admin_setting_country_rate_value = State()
    admin_setting_payment_number = State()
    admin_adding_balance_id = State()
    admin_adding_balance_amount = State()
    admin_viewing_balance_id = State()
    admin_broadcasting = State()

# --- API Helper ---
class SMSBowerAPI:
    BASE_URL = "https://smsbower.page/stubs/handler_api.php"
    
    @staticmethod
    async def request(action, params=None):
        if params is None: params = {}
        params['api_key'] = SMS_BOWER_API_KEY
        params['action'] = action
        for attempt in range(1, 4):  # retry up to 3 times
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(SMSBowerAPI.BASE_URL, params=params, timeout=10.0)
                    return response.text
            except Exception as e:
                if attempt == 3:
                    logging.error(f"SMSBowerAPI.{action} failed after 3 attempts: {e}")
                    return None
                wait = attempt  # 1s, 2s
                logging.warning(f"SMSBowerAPI.{action} attempt {attempt} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    @staticmethod
    async def get_prices(service=None, country=None):
        params = {}
        if service: params['service'] = service
        if country: params['country'] = country
        return await SMSBowerAPI.request('getPricesV3', params)

    @staticmethod
    async def get_number(service, country, max_price=None, provider_id=None):
        params = {'service': service, 'country': country, 'userID': SMS_BOWER_USER_ID}
        if max_price: params['maxPrice'] = max_price
        if provider_id: params['providerIds'] = provider_id
        return await SMSBowerAPI.request('getNumber', params)

    @staticmethod
    async def get_status(activation_id):
        return await SMSBowerAPI.request('getStatus', {'id': activation_id})

    @staticmethod
    async def set_status(activation_id, status):
        return await SMSBowerAPI.request('setStatus', {'id': activation_id, 'status': status})

# --- Database Helper ---
class DB:
    @staticmethod
    async def get_user(user_id, username="No Username"):
        def _get():
            ref = db.reference(f'users/{user_id}')
            user = ref.get()
            if not user:
                user = {'balance': 0.0, 'username': username, 'total_numbers': 0, 'total_otps': 0, 'total_cost': 0.0}
                ref.set(user)
            return user
        return await retry_async(
            lambda: asyncio.to_thread(_get),
            retries=3, delay=1.0, label=f"DB.get_user({user_id})"
        )

    @staticmethod
    async def update_user(user_id, data):
        await retry_async(
            lambda: asyncio.to_thread(db.reference(f'users/{user_id}').update, data),
            retries=3, delay=1.0, label=f"DB.update_user({user_id})"
        )

    @staticmethod
    async def get_settings():
        def _get():
            ref = db.reference('settings')
            settings = ref.get()
            if not settings:
                settings = {'dollar_rate': 150.0, 'bkash_number': 'Not Set', 'nagad_number': 'Not Set', 'services': {}}
                ref.set(settings)
            return settings
        return await retry_async(
            lambda: asyncio.to_thread(_get),
            retries=3, delay=1.0, label="DB.get_settings"
        )

    @staticmethod
    async def update_settings(data):
        await retry_async(
            lambda: asyncio.to_thread(db.reference('settings').update, data),
            retries=3, delay=1.0, label="DB.update_settings"
        )

# --- Keyboards ---
def main_menu_keyboard():
    kb = [
        [KeyboardButton(text="⚡ Get Number"), KeyboardButton(text="🔐 2FA Code")],
        [KeyboardButton(text="📊 My Statas"), KeyboardButton(text="💳 Deposit")],
        [KeyboardButton(text="☎️ Support")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu_keyboard():
    kb = [
        [KeyboardButton(text="➕ Add Service"), KeyboardButton(text="❌ Delete Service")],
        [KeyboardButton(text="📋 View Service"), KeyboardButton(text="🌍 Add Country")],
        [KeyboardButton(text="🗑 Delete Country"), KeyboardButton(text="🗺 View Country")],
        [KeyboardButton(text="💵 Set $ Rate"), KeyboardButton(text="📞 Add Number")],
        [KeyboardButton(text="👀 View Number"), KeyboardButton(text="💸 Add Balance")],
        [KeyboardButton(text="👁️ View Balance"), KeyboardButton(text="📢 Broadcast")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- Bot Initialization ---
bot = Bot(token=API_TOKEN)
async def fb_get(path):
    import asyncio
    from firebase_admin import db
    return await asyncio.to_thread(db.reference(path).get)
async def fb_set(path, data):
    import asyncio
    from firebase_admin import db
    await asyncio.to_thread(db.reference(path).set, data)
async def fb_update(path, data):
    import asyncio
    from firebase_admin import db
    await asyncio.to_thread(db.reference(path).update, data)
async def fb_delete(path):
    import asyncio
    from firebase_admin import db
    await asyncio.to_thread(db.reference(path).delete)

# --- Retry helper: retries async calls on failure with exponential backoff ---
async def retry_async(coro_fn, retries=3, delay=1.0, label="operation"):
    """Retry an async callable up to `retries` times with exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            if attempt == retries:
                logging.error(f"[{label}] Failed after {retries} attempts: {e}")
                raise
            wait = delay * (2 ** (attempt - 1))  # 1s, 2s, 4s
            logging.warning(f"[{label}] Attempt {attempt} failed: {e}. Retrying in {wait}s...")
            await asyncio.sleep(wait)

# --- Simple settings cache to reduce Firebase reads ---
_settings_cache = {'data': None, 'ts': 0}
SETTINGS_CACHE_TTL = 30  # seconds

async def get_cached_settings():
    now = time.time()
    if _settings_cache['data'] is None or (now - _settings_cache['ts']) > SETTINGS_CACHE_TTL:
        _settings_cache['data'] = await DB.get_settings()
        _settings_cache['ts'] = now
    return _settings_cache['data']

def invalidate_settings_cache():
    _settings_cache['data'] = None
    _settings_cache['ts'] = 0

# --- Cached bot username (fetched once at startup) ---
_bot_username = None
async def get_bot_username():
    global _bot_username
    if not _bot_username:
        me = await bot.get_me()
        _bot_username = me.username
    return _bot_username

dp = Dispatcher(storage=MemoryStorage())

# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    await DB.get_user(user_id, username)
    if user_id == ADMIN_ID:
        await message.answer("🛠 Admin Panel Activated\nWelcome back, Boss!", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    else:
        await message.answer("🚀 Welcome to Active Number!\nGet numbers and receive OTPs instantly.", 
                             reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# --- Get Number Flow ---
@dp.message(F.text == "⚡ Get Number")
async def get_number_start(message: types.Message):
    settings = await get_cached_settings()
    services = settings.get('services', {})
    if not services:
        await message.answer("❌ No services configured. Please contact admin.")
        return
    buttons = [[InlineKeyboardButton(text=get_service_name(s), callback_data=f"srv_{s}")] for s in services.keys()]
    await message.answer("🎯 Select Service", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("srv_"))
async def select_country(callback: types.CallbackQuery):
    service_name = callback.data.split("_")[1]
    settings = await get_cached_settings()
    countries = settings.get('services', {}).get(service_name, {}).get('countries', [])
    if not countries:
        await callback.message.edit_text("❌ No countries set for this service.")
        return
    
    display_service = get_service_name(service_name)
    await callback.message.edit_text(f"⏳ Fetching live prices for {display_service}...", parse_mode="Markdown")
    
    global_rate = settings.get('dollar_rate', 150.0)
    country_rates = settings.get('country_rates', {})
    buttons = []
    
    # Optimized: Fetch prices for all countries in parallel
    async def fetch_price(c):
        try:
            c_code = str(c['code'])
            res_str = await SMSBowerAPI.get_prices(service=service_name, country=c_code)
            if res_str:
                price_data = json.loads(res_str)
                if c_code in price_data and service_name in price_data[c_code]:
                    providers = price_data[c_code][service_name]
                    min_cost = float('inf')

                    # First pass: find the minimum price
                    for prov_id, prov_data in providers.items():
                        count = int(prov_data.get('count', 0))
                        price = float(prov_data.get('price', 9999.0))
                        if count > 0 and price < min_cost:
                            min_cost = price

                    if min_cost == float('inf'):
                        return None

                    # Second pass: collect ALL providers with min price and sum quantities
                    total_count = 0
                    best_provs = []
                    for prov_id, prov_data in providers.items():
                        count = int(prov_data.get('count', 0))
                        price = float(prov_data.get('price', 9999.0))
                        if count > 0 and price == min_cost:
                            total_count += count
                            best_provs.append(prov_id)

                    if best_provs:
                        rate = country_rates.get(c_code, global_rate)
                        bdt_price = min_cost * rate
                        usd_str = f"{min_cost:.3f}"
                        safe_c_name = c['name'][:12]
                        flag = get_country_flag(c_code)
                        # Join provider IDs with '-' so we can try each on buy
                        joined_provs = "-".join(best_provs)
                        return [InlineKeyboardButton(
                            text=f"{flag} {c['name']} - {bdt_price:.2f} BDT ({total_count} Qty)",
                            callback_data=f"buy_{service_name}_{c_code}_{usd_str}_{joined_provs}_{safe_c_name}"
                        )]
        except: pass
        return None

    results = await asyncio.gather(*(fetch_price(c) for c in countries))
    buttons = [res for res in results if res is not None]
    
    if not buttons:
        # Even on no-result, show Back button
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Services", callback_data="back_to_services")]
        ])
        await callback.message.edit_text(
            f"❌ No numbers available for {display_service} right now.\n(Make sure the API code is correct)",
            reply_markup=back_kb
        )
    else:
        # Append Back button as last row
        buttons.append([InlineKeyboardButton(text="🔙 Back to Services", callback_data="back_to_services")])
        await callback.message.edit_text(f"🌍 Select Country for {display_service}",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_services")
async def back_to_services(callback: types.CallbackQuery):
    settings = await get_cached_settings()
    services = settings.get('services', {})
    if not services:
        await callback.message.edit_text("❌ No services configured. Please contact admin.")
        return
    buttons = [[InlineKeyboardButton(text=get_service_name(s), callback_data=f"srv_{s}")] for s in services.keys()]
    await callback.message.edit_text("🎯 Select Service", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_number(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    # parts: [buy, service, c_code, usd_price, provIds..., c_name]
    # c_name is always the LAST part; prov_ids is everything between index 4 and last
    srv = parts[1]
    c_code = parts[2]
    usd_price_str = parts[3]
    c_name = parts[-1]
    prov_id = "_".join(parts[4:-1])  # rejoin in case provider IDs had underscores
    
    settings = await get_cached_settings()
    # Use per-country rate if set, otherwise fall back to global rate
    country_rates = settings.get('country_rates', {})
    dollar_rate = country_rates.get(c_code, settings.get('dollar_rate', 150.0))
    usd_price = float(usd_price_str)
    bdt_price = usd_price * dollar_rate
    
    user = await DB.get_user(callback.from_user.id)
    if user['balance'] < bdt_price:
        await callback.answer("❌ Insufficient Balance!", show_alert=True)
        return

    await callback.message.edit_text("⏳ Generating Number...", parse_mode="Markdown")

    # Try each provider ID sequentially (handles tied-price multiple providers)
    prov_ids = prov_id.split("-")
    res = None
    for pid in prov_ids:
        res = await SMSBowerAPI.get_number(srv, c_code, max_price=usd_price, provider_id=pid)
        if res and res.startswith("ACCESS_NUMBER"):
            break

    if res and res.startswith("ACCESS_NUMBER"):
        # Bug fix #4: use split(":", 2) to safely handle phone numbers with colons
        split_res = res.split(":", 2)
        if len(split_res) < 3:
            await callback.message.edit_text(f"❌ API Error: Unexpected response format: {res}")
            return
        _, act_id, phone = split_res
        # Full country name with flag from stored data
        flag = get_country_flag(c_code)
        country_display = f"{flag} {c_name}"
        
        def _set_active():
            db.reference(f'active_activations/{act_id}').set({
                'user_id': callback.from_user.id,
                'service': get_service_name(srv),
                'country': country_display,
                'c_code': c_code,
                'price': bdt_price, 'phone': phone, 'timestamp': time.time()
            })
        await asyncio.to_thread(_set_active)
        await DB.update_user(callback.from_user.id, {'total_numbers': user['total_numbers'] + 1})
        
        msg = (f"✅ Number Generated Successfully!\n\n"
               f"🌍 Country: {country_display}\n"
               f"☎ Your Number: `{phone}`\n\n"
               "Waiting for OTP... Check your Inbox or the Group.")
        kb = [[InlineKeyboardButton(text="❌ Cancel Number", callback_data=f"change_{act_id}"),
               InlineKeyboardButton(text="👥 OTP Group", url="https://t.me/Active_Number_Otp")]]
        await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
        asyncio.create_task(poll_otp(act_id, callback.message))
    else:
        await callback.message.edit_text(f"❌ API Error: {res}")

async def poll_otp(act_id, message: types.Message):
    # Fetch data once at the start to avoid hammering Firebase
    try:
        data = await asyncio.to_thread(db.reference(f'active_activations/{act_id}').get)
    except Exception as e:
        logging.error(f"Firebase error in poll_otp init [{act_id}]: {e}")
        return

    if not data:
        return

    # Wait for 20 minutes (1200 seconds) for the webhook to process the OTP
    await asyncio.sleep(1200)

    # Check if the activation still exists (meaning webhook never received the OTP)
    try:
        current_data = await asyncio.to_thread(db.reference(f'active_activations/{act_id}').get)
    except Exception as e:
        logging.error(f"Firebase error checking timeout [{act_id}]: {e}")
        return

    if current_data:
        # Timeout notification to user
        try:
            await SMSBowerAPI.set_status(act_id, 8)
        except: pass
        await asyncio.to_thread(db.reference(f'active_activations/{act_id}').delete)
        try:
            await message.answer(
                "⏰ Time Expired!\n"
                f"☎ Number: `{data['phone']}`\n"
                "No OTP received within 20 minutes. The number has been cancelled.",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        except: pass





@dp.callback_query(F.data == "start_over")
async def start_over_handler(callback: types.CallbackQuery):
    await callback.message.delete()
    await get_number_start(callback.message)

@dp.callback_query(F.data.startswith("change_"))
async def change_num(callback: types.CallbackQuery):
    act_id = callback.data.split("_")[1]
    await SMSBowerAPI.set_status(act_id, 8)
    await asyncio.to_thread(db.reference(f'active_activations/{act_id}').delete)
    await callback.message.edit_text("❌ Number Cancelled. You can request a new one.")

# --- Deposit ---
@dp.message(F.text == "💳 Deposit")
async def dep_start(message: types.Message):
    kb = [[InlineKeyboardButton(text="Bkash", callback_data="dep_bkash"),
           InlineKeyboardButton(text="Nagad", callback_data="dep_nagad")]]
    await message.answer("💳 Choose Deposit Method", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dep_"))
async def dep_method(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    await state.update_data(method=method)
    await callback.message.answer(f"💰 How much BDT to deposit via {method.capitalize()}?", parse_mode="Markdown")
    await state.set_state(BotStates.depositing_amount)

@dp.message(BotStates.depositing_amount)
async def dep_amt(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.strip())
        if amt <= 0:
            raise ValueError("Amount must be positive")
        data = await state.get_data()
        settings = await DB.get_settings()
        num = settings.get(f"{data['method']}_number", "Not Set")
        card = (f"━━━━━━━━━━━━━━━━━━\n💎 DEPOSIT REQUEST\n━━━━━━━━━━━━━━━━━━\n"
                f"💵 Amount: {amt} BDT\n🏦 Method: {data['method'].capitalize()}\n"
                f"☎ Send to: `{num}`\n━━━━━━━━━━━━━━━━━━\nClick Proof to submit TxID.")
        kb = [[InlineKeyboardButton(text="📩 Proof", callback_data="proof"),
               InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_dep")]]
        await state.update_data(amount=amt)
        card_msg = await message.answer(card, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
        # Save card message id so we can delete it later if needed
        await state.update_data(card_message_id=card_msg.message_id, card_chat_id=card_msg.chat.id)
    except:
        await message.answer(
            "⚠️ Invalid amount!\nPlease enter a valid number (e.g. `100` or `250.50`).",
            parse_mode="Markdown"
        )
        # Stay in the same state so user can try again

@dp.callback_query(F.data == "cancel_dep")
async def cancel_deposit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Deposit Request Cancelled.", parse_mode="Markdown")

@dp.callback_query(F.data == "proof")
async def proof_tx(callback: types.CallbackQuery, state: FSMContext):
    # Guard: verify state still has deposit data (lost on bot restart)
    data = await state.get_data()
    if not data.get('amount') or not data.get('method'):
        await state.clear()
        await callback.message.answer(
            "⚠️ Session expired. Please start the deposit process again.",
            reply_markup=main_menu_keyboard()
        )
        return
    await callback.message.answer("📩 Enter your Transaction ID (TxID):", parse_mode="Markdown")
    await state.set_state(BotStates.entering_txid)

@dp.message(BotStates.entering_txid)
async def tx_submit(message: types.Message, state: FSMContext):
    txid = message.text.strip().upper()
    data = await state.get_data()

    # Guard: if state data is missing (bot restarted), abort gracefully
    amount = data.get('amount')
    method = data.get('method')
    if not amount or not method:
        await state.clear()
        await message.answer(
            "⚠️ Session expired. Please start the deposit process again.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # Check for duplicate TxID
    reqs = await fb_get('deposit_requests')
    if reqs:
        for r_data in reqs.values():
            existing_txid = str(r_data.get('txid')).strip().upper()
            if existing_txid == txid:
                # Edit the deposit card to show it's cancelled
                card_msg_id = data.get('card_message_id')
                if card_msg_id:
                    try:
                        await bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=card_msg_id,
                            text="━━━━━━━━━━━━━━━━━━\n💎 DEPOSIT REQUEST\n━━━━━━━━━━━━━━━━━━\n❌ Cancelled — Duplicate TxID",
                            parse_mode="Markdown"
                        )
                    except: pass
                await message.answer(
                    "❌ This Transaction ID has already been used!",
                    parse_mode="Markdown"
                )
                await message.answer(
                    "❌ Deposit Request Cancelled.",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
                await state.clear()
                return

    req_id = f"dep_{int(time.time())}"
    await fb_set(f'deposit_requests/{req_id}', {
        'user_id': message.from_user.id, 'amount': amount, 'method': method,
        'txid': txid, 'status': 'pending', 'timestamp': time.time(),
        'username': message.from_user.username or 'No Username'
    })
    await message.answer("✅ Request Sent! Pending Admin or Auto-approval.", reply_markup=main_menu_keyboard())
    await state.clear()

# --- Other User Commands ---
@dp.message(F.text == "📊 My Statas")
async def stats(message: types.Message):
    u = await DB.get_user(message.from_user.id)
    await message.answer(f"📊 YOUR STATUS & BALANCE\n━━━━━━━━━━━━━━━━━━\n\n💵 Current Balance: {u['balance']:.2f} BDT\n\n☎ Total Taken: {u['total_numbers']}\n📩 Total OTPs: {u['total_otps']}\n💰 Total Cost: {u['total_cost']:.2f} BDT", parse_mode="Markdown")

@dp.message(F.text == "🔐 2FA Code")
async def fa_start(message: types.Message, state: FSMContext):
    await message.answer("🔐 Send your 2FA Secret Key:")
    await state.set_state(BotStates.entering_2fa_key)

@dp.message(BotStates.entering_2fa_key)
async def fa_gen(message: types.Message, state: FSMContext):
    try:
        code = pyotp.TOTP(message.text.replace(" ", "")).now()
        await message.answer(f"🔐 Your 2FA Code: `{code}`", parse_mode="Markdown")
    except: await message.answer("❌ Invalid Key.")
    await state.clear()

@dp.message(F.text.endswith("Support"))
async def support(message: types.Message):
    # Telegram DOES NOT allow tg://user?id= in buttons, so you MUST use a t.me link with your username here!
    # Please change "your_telegram_username" to your actual username (e.g., "mosharofdu41")
    msg = "☎️ Support Information\n\n👨‍💼 Admin: [Click Here to Message Admin](tg://user?id=1309805034)"
    kb = [
        [InlineKeyboardButton(text="💬 Contact Admin", url="https://t.me/Active_Number_Support")],
        [InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/Active_Number_Update")]
    ]
    await message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# --- Admin Panel Handlers ---

@dp.message(F.text == "➕ Add Service")
async def adm_add_srv(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("➕ Enter Service API Code\n(e.g., `fb` for Facebook, `tg` for Telegram, `go` for Google):\n\n*⚠️ You MUST use the correct API shortcode, otherwise the bot cannot fetch numbers.*", parse_mode="Markdown")
        await state.set_state(BotStates.admin_adding_service)

@dp.message(BotStates.admin_adding_service)
async def adm_add_srv_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    # Use 'name' property to ensure the node is not deleted by Firebase (since empty lists/objects are removed)
    await fb_set(f'settings/services/{name}', {'name': name, 'countries': []})
    await message.answer(f"✅ Service '{name}' added successfully!", parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "📋 View Service")
async def adm_view_srv(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        srvs = await fb_get('settings/services')
        if not srvs:
            await message.answer("📋 No services added yet.", parse_mode="Markdown")
            return
        msg = "📋 Services List:\n" + "\n".join([f"🔹 {s}" for s in srvs.keys()])
        await message.answer(msg, parse_mode="Markdown")

@dp.message(F.text == "❌ Delete Service")
async def adm_del_srv(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        srvs = await fb_get('settings/services')
        if not srvs:
            await message.answer("📋 No services to delete.", parse_mode="Markdown")
            return
        kb = [[InlineKeyboardButton(text=f"🗑 {s}", callback_data=f"ds_{s}")] for s in srvs.keys()]
        await message.answer("❌ Select Service to Delete:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("ds_"))
async def adm_del_srv_conf(callback: types.CallbackQuery):
    srv = callback.data.split("_")[1]
    kb = [[InlineKeyboardButton(text="✅ Yes Delete", callback_data=f"dsc_{srv}"),
           InlineKeyboardButton(text="🔙 Cancel", callback_data="adm_cancel")]]
    await callback.message.edit_text(f"❓ Are you sure you want to delete '{srv}'?", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dsc_"))
async def adm_del_srv_exec(callback: types.CallbackQuery):
    srv = callback.data.split("_")[1]
    await fb_delete(f'settings/services/{srv}')
    await callback.message.edit_text(f"✅ Service '{srv}' deleted.", parse_mode="Markdown")

@dp.message(F.text == "🌍 Add Country")
async def adm_add_c(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        srvs = await fb_get('settings/services')
        if not srvs:
            await message.answer("❌ Add a service first.")
            return
        kb = [[InlineKeyboardButton(text=f"🔹 {s}", callback_data=f"ac_{s}")] for s in srvs.keys()]
        await message.answer("🌍 Select Service to add Country:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("ac_"))
async def adm_add_c_sel(callback: types.CallbackQuery, state: FSMContext):
    srv = callback.data.split("_")[1]
    await state.update_data(srv=srv)
    await callback.message.answer(f"🌍 Enter details for {srv}:\nFormat: `Name Code` (e.g. `Russia 0`)", parse_mode="Markdown")
    await state.set_state(BotStates.admin_adding_country_details)

@dp.message(BotStates.admin_adding_country_details)
async def adm_add_c_fin(message: types.Message, state: FSMContext):
    try:
        parts = message.text.rsplit(" ", 1)
        if len(parts) < 2: raise Exception("Invalid format")
        n, c = parts[0], parts[1]
        data = await state.get_data()
        srv = data['srv']
        
        def _add_country():
            ref = db.reference(f'settings/services/{srv}/countries')
            countries = ref.get() or []
            countries.append({'name': n, 'code': c})
            ref.set(countries)
        await asyncio.to_thread(_add_country)
        
        # Ensure the service node itself has its 'name' property preserved
        await fb_update(f'settings/services/{srv}', {'name': srv})
        invalidate_settings_cache()
        
        await message.answer(f"✅ Added {n} (Code: {c}) to {srv}!", parse_mode="Markdown")
    except Exception as e: 
        await message.answer(f"❌ Error: {str(e)}. Use `Name Code`.")
    await state.clear()

@dp.message(F.text == "🗺 View Country")
async def adm_view_cnt(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        srvs = await fb_get('settings/services')
        if not srvs:
            await message.answer("📋 No services available.")
            return
        kb = [[InlineKeyboardButton(text=f"🔹 {s}", callback_data=f"vc_{s}")] for s in srvs.keys()]
        await message.answer("🗺 Select Service to view countries:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("vc_"))
async def adm_view_cnt_res(callback: types.CallbackQuery):
    srv = callback.data.split("_")[1]
    countries = await fb_get(f'settings/services/{srv}/countries')
    if not countries:
        await callback.message.edit_text(f"🗺 No countries added for {srv}.", parse_mode="Markdown")
        return
    msg = f"🌍 Countries for {srv}:\n" + "\n".join([f"📍 {c['name']} (Code: {c['code']})" for c in countries])
    await callback.message.edit_text(msg, parse_mode="Markdown")

@dp.message(F.text == "🗑 Delete Country")
async def adm_del_cnt_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        srvs = await fb_get('settings/services')
        kb = [[InlineKeyboardButton(text=f"🔹 {s}", callback_data=f"dc_{s}")] for s in srvs.keys()]
        await message.answer("🗑 Select Service to delete country:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dc_"))
async def adm_del_cnt_list(callback: types.CallbackQuery):
    srv = callback.data.split("_")[1]
    countries = await fb_get(f'settings/services/{srv}/countries')
    if not countries:
        await callback.message.edit_text("❌ No countries to delete.")
        return
    kb = [[InlineKeyboardButton(text=f"📍 {c['name']}", callback_data=f"dcc_{srv}_{c['code']}")] for c in countries]
    await callback.message.edit_text(f"🗑 Select Country to delete from {srv}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dcc_"))
async def adm_del_cnt_exec(callback: types.CallbackQuery):
    srv, code = callback.data.split("_")[1], callback.data.split("_")[2]
    ref = db.reference(f'settings/services/{srv}/countries')
    countries = ref.get()
    new_countries = [c for c in countries if str(c['code']) != str(code)]
    ref.set(new_countries)
    await callback.message.edit_text("✅ Country deleted.", parse_mode="Markdown")

@dp.message(F.text == "💸 Add Balance")
async def adm_add_bal_id(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👤 Enter User Telegram ID:", parse_mode="Markdown")
        await state.set_state(BotStates.admin_adding_balance_id)

@dp.message(BotStates.admin_adding_balance_id)
async def adm_add_bal_amt(message: types.Message, state: FSMContext):
    await state.update_data(uid=message.text)
    await message.answer("💵 Enter amount to add (BDT):", parse_mode="Markdown")
    await state.set_state(BotStates.admin_adding_balance_amount)

@dp.message(BotStates.admin_adding_balance_amount)
async def adm_add_bal_fin(message: types.Message, state: FSMContext):
    try:
        d = await state.get_data()
        uid = d['uid']
        amt_str = message.text.strip()
        amt = float(amt_str)
        
        # We need to make sure we use async db read/write
        def _update_bal():
            u_ref = db.reference(f'users/{uid}')
            u = u_ref.get() or {'balance': 0.0}
            new_bal = (u.get('balance') or 0.0) + amt
            u_ref.update({'balance': new_bal})
            return new_bal
            
        new_bal = await asyncio.to_thread(_update_bal)
        
        if amt < 0:
            deducted = abs(amt)
            await message.answer(f"✅ Deducted {deducted} BDT from User {uid}.\nNew Balance: {new_bal} BDT.", parse_mode="Markdown")
            try: await bot.send_message(uid, f"📉 Balance Deducted\nAdmin has deducted {deducted} BDT from your account.", parse_mode="Markdown")
            except: pass
        else:
            await message.answer(f"✅ Added {amt} BDT to User {uid}.\nNew Balance: {new_bal} BDT.", parse_mode="Markdown")
            try: await bot.send_message(uid, f"💰 Balance Added!\nAdmin has added {amt} BDT to your account.", parse_mode="Markdown")
            except: pass
    except ValueError:
        await message.answer("❌ Error. Check values.")
    await state.clear()

@dp.message(F.text == "👁️ View Balance")
async def adm_view_bal_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👁️ Enter User Telegram ID:", parse_mode="Markdown")
        await state.set_state(BotStates.admin_viewing_balance_id)

@dp.message(BotStates.admin_viewing_balance_id)
async def adm_view_bal_fin(message: types.Message, state: FSMContext):
    uid = message.text.strip()
    try:
        def _get_bal():
            return db.reference(f'users/{uid}').get()
            
        u = await asyncio.to_thread(_get_bal)
        if u:
            bal = u.get('balance', 0.0)
            await message.answer(f"👁️ User {uid} Balance: {bal} BDT", parse_mode="Markdown")
        else:
            await message.answer(f"❌ User {uid} not found in database.", parse_mode="Markdown")
    except Exception as e:
        await message.answer("❌ Error fetching balance.")
    await state.clear()

@dp.message(F.text == "📢 Broadcast")
async def br_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("📢 Send message to broadcast:", parse_mode="Markdown")
        await state.set_state(BotStates.admin_broadcasting)

@dp.message(BotStates.admin_broadcasting)
async def br_exec(message: types.Message, state: FSMContext):
    users = await fb_get('users')
    if users:
        count = 0
        for uid in users:
            try:
                await bot.send_message(uid, message.text)
                count += 1
            except: pass
        await message.answer(f"✅ Broadcast sent to {count} users.", parse_mode="Markdown")
    else: await message.answer("❌ No users found.")
    await state.clear()

@dp.message(F.text == "💵 Set $ Rate")
async def adm_set_rate(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    settings = await DB.get_settings()
    services = settings.get('services', {})
    if not services:
        await message.answer("❌ No services configured.")
        return
    buttons = [[InlineKeyboardButton(text=get_service_name(s), callback_data=f"rate_srv_{s}")] for s in services.keys()]
    await message.answer("💵 Select Service to set rate for:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("rate_srv_"))
async def adm_rate_srv(callback: types.CallbackQuery, state: FSMContext):
    srv = callback.data.split("rate_srv_")[1]
    await state.update_data(rate_srv=srv)
    settings = await DB.get_settings()
    countries = settings.get('services', {}).get(srv, {}).get('countries', [])
    if not countries:
        await callback.message.edit_text("❌ No countries added to this service yet.")
        return
    buttons = []
    for c in countries:
        flag = get_country_flag(str(c['code']))
        buttons.append([InlineKeyboardButton(
            text=f"{flag} {c['name']}",
            callback_data=f"rate_c_{c['code']}"
        )])
    await callback.message.edit_text(f"🌍 Select Country to set rate for ({get_service_name(srv)}):",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("rate_c_"))
async def adm_rate_country(callback: types.CallbackQuery, state: FSMContext):
    c_code = callback.data.split("rate_c_")[1]
    await state.update_data(rate_c_code=c_code)
    flag = get_country_flag(c_code)
    settings = await DB.get_settings()
    current = settings.get('country_rates', {}).get(c_code, settings.get('dollar_rate', 150.0))
    await callback.message.edit_text(
        f"💵 Set dollar rate for {flag} country code {c_code}\n"
        f"Current rate: {current} BDT per USD\n\n"
        "Send new rate (e.g. 120):"
    )
    await state.set_state(BotStates.admin_setting_country_rate_value)

@dp.message(BotStates.admin_setting_country_rate_value)
async def adm_set_country_rate_val(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.strip())
        d = await state.get_data()
        c_code = d['rate_c_code']

        def _save():
            ref = db.reference('settings/country_rates')
            existing = ref.get() or {}
            existing[c_code] = rate
            ref.set(existing)
        await asyncio.to_thread(_save)

        flag = get_country_flag(c_code)
        await message.answer(f"✅ Rate set: {flag} Country {c_code} = {rate} BDT per USD")
    except ValueError:
        await message.answer("❌ Invalid rate. Enter a number like 120 or 125.5")
    await state.clear()

@dp.message(F.text == "📞 Add Number")
async def adm_add_pnum(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton(text="📱 Bkash", callback_data="sn_bkash"),
               InlineKeyboardButton(text="📱 Nagad", callback_data="sn_nagad")]]
        await message.answer("📞 Select Payment Method:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("sn_"))
async def adm_sn_sel(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    await state.update_data(method=method)
    await callback.message.answer(f"📞 Enter {method.capitalize()} Number:", parse_mode="Markdown")
    await state.set_state(BotStates.admin_setting_payment_number)

@dp.message(BotStates.admin_setting_payment_number)
async def adm_sn_val(message: types.Message, state: FSMContext):
    d = await state.get_data()
    await fb_update('settings', {f"{d['method']}_number": message.text})
    await message.answer(f"✅ {d['method'].capitalize()} number updated!", parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "👀 View Number")
async def adm_view_nums(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        s = await fb_get('settings')
        msg = (f"📞 Payment Numbers\n━━━━━━━━━━━━━━━━━━\n"
               f"🔹 Bkash: `{s.get('bkash_number', 'Not Set')}`\n"
               f"🔹 Nagad: `{s.get('nagad_number', 'Not Set')}`")
        await message.answer(msg, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_cancel")
async def adm_cancel(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Action Cancelled.", parse_mode="Markdown")

# --- Main ---
async def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try: await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Bot Crashed: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
