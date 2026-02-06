import os
import time
import requests
import json
import random

def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PROJECT_ID = os.environ.get('WEBSIM_PROJECT_ID')

if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print("Error: Please set your BOT_TOKEN in the .env file.")
    exit()

if not PROJECT_ID:
    print("Error: Please set WEBSIM_PROJECT_ID in the .env file.")
    exit()

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

USER_LANG = {}

MESSAGES = {
    'en': {
        'welcome': "Hello! I'm here to make any image you want in mind come true 🚀\n\nPlease send me a text description.",
        'generating': [
            "Consulting the artist... 🎨",
            "Mixing magic potions... 🧪",
            "Dreaming up your image... 💭",
            "Summoning the pixels... 🪄",
            "Asking the AI gods... 🤖"
        ],
        'error': "Sorry, I couldn't generate that image. Please try again.",
        'caption': "✨ Here is your dream:",
        'prompt_needed': "Please select a language first."
    },
    'ar': {
        'welcome': "مرحباً! أنا هنا لأحقق أي صورة تخطر في بالك 🚀\n\nالرجاء إرسال وصف للصورة.",
        'generating': [
            "جارٍ استشارة الفنان... 🎨",
            "جارٍ خلط الوصفات السحرية... 🧪",
            "أحلم بصورتك... 💭",
            "أستدعي البيكسلات... 🪄",
            "جارٍ المعالجة الذكية... 🤖"
        ],
        'error': "عذراً، لم أتمكن من إنشاء الصورة. حاول مرة أخرى.",
        'caption': "✨ ها هو حلمك:",
        'prompt_needed': "الرجاء اختيار اللغة أولاً."
    }
}

def google_translate(text, target_lang="en"):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            return "".join([item[0] for item in result[0]])
    except Exception as e:
        print(f"Translation error: {e}")
    return text

def generate_image_url(prompt):
    url = "https://api.websim.com/api/v1/inference/run_image_generation"
    
    translated_prompt = google_translate(prompt, "en")
    print(f"Generating for: {translated_prompt}")

    payload = {
        "project_id": PROJECT_ID,
        "prompt": translated_prompt,
        "aspect_ratio": "1:1"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-A025F Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.61 Mobile Safari/537.36",
        "Content-Type": "application/json",
        "origin": "https://websim.com",
        "referer": "https://websim.com/"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if 'url' in data:
            return data['url']
        else:
            print(f"API Error: {data}")
    except Exception as e:
        print(f"Generation Error: {e}")
    return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {'timeout': 100, 'offset': offset}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except:
        return {}

def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    requests.post(url, json=payload)

def send_photo(chat_id, photo_url, caption):
    url = f"{BASE_URL}/sendPhoto"
    requests.post(url, json={'chat_id': chat_id, 'photo': photo_url, 'caption': caption})

def answer_callback_query(callback_query_id, text=None):
    url = f"{BASE_URL}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id}
    if text:
        payload['text'] = text
    requests.post(url, json=payload)

def show_language_selection(chat_id):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "English 🇬🇧", "callback_data": "lang_en"},
                {"text": "العربية 🇸🇦", "callback_data": "lang_ar"}
            ]
        ]
    }
    send_message(chat_id, "Please choose your language / الرجاء اختيار لغتك", reply_markup=keyboard)

def main():
    print("Bot is running...")
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            if "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    if "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data = query["data"]
                        query_id = query["id"]

                        if data == "lang_en":
                            USER_LANG[chat_id] = 'en'
                            answer_callback_query(query_id, "Language set to English")
                            send_message(chat_id, MESSAGES['en']['welcome'])
                        elif data == "lang_ar":
                            USER_LANG[chat_id] = 'ar'
                            answer_callback_query(query_id, "تم اختيار اللغة العربية")
                            send_message(chat_id, MESSAGES['ar']['welcome'])
                        
                        continue

                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]
                        
                        if text == "/start":
                            show_language_selection(chat_id)
                        else:
                            lang = USER_LANG.get(chat_id, 'en')
                            
                            loading_msg = random.choice(MESSAGES[lang]['generating'])
                            send_message(chat_id, loading_msg)
                            
                            image_url = generate_image_url(text)
                            
                            if image_url:
                                send_photo(chat_id, image_url, f"{MESSAGES[lang]['caption']} {text}")
                            else:
                                send_message(chat_id, MESSAGES[lang]['error'])
            
            time.sleep(1)
        except Exception as e:
            print(f"Error loop: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
