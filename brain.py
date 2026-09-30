import datetime
import webbrowser
import os
import sys
import keyboard 
import urllib.request 
import urllib.parse
import json 
import xml.etree.ElementTree as ET 
import threading 
import telebot   
from rapidfuzz import fuzz
from speaker import speak, play_activation_sound
from listener import start_listening

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Глобальный колбек для интерфейса
gui_callback = None

# ==========================================
# 📱 НАСТРОЙКИ ТЕЛЕГРАМ-БОТА 
# ==========================================
TELEGRAM_BOT_TOKEN = "ВАШ ТОКЕН БОТА" 
TELEGRAM_ALLOWED_ID = "ВАШ ТОКЕН" 

# ==========================================
# 🧠 ГЛОБАЛЬНЫЕ СОСТОЯНИЯ
# ==========================================
jarvis_is_sleeping = False  # Флаг режима ожидания

WAKE_WORDS = ["джарвис", "жарвис", "чарвис", "дарвис", "джервис", "джонс", "завес", "жадность", "джой с", "занавес", "зависть", "джойс"]

# --- СЛОВАРЬ КОМАНД ---
COMMANDS = {
    # УПРАВЛЕНИЕ САМИМ ИИ
    "jarvis_off": ["отключись", "выключись", "заверши работу", "отключение", "отключить питание", "умри", "пока"],
    "jarvis_sleep": ["режим ожидания", "перейди в режим ожидания", "спящий режим для себя", "усни", "засни", "отдохни", "никого не слушай"],
    "jarvis_wake": ["проснись", "очнись", "выходи из сна", "вставай", "ты мне нужен", "просыпайся"],

    "time": ["сколько времени", "который час", "текущее время", "скажи время", "время"],
    "weather_now": ["погода", "какая сейчас погода", "что за окном", "метеосводка"], 
    "weather_tomorrow": ["погода на завтра", "прогноз на завтра", "что будет завтра", "завтра погода"], 
    "news": ["новости", "сводка новостей", "что нового", "утренние новости", "расскажи новости", "какие новости"],
    
    "search_anime": ["включи аниме", "найди аниме", "покажи аниме", "аниме"],
    "search_movie": ["включи фильм", "найди фильм", "включи кино", "включи сериал", "фильм", "сериал"],
    "open_website": ["открой сайт", "перейди на сайт", "открой страницу", "сайт"],
    
    "welcome_home": ["папочка дома", "я вернулся", "я дома", "запускай протокол дом"],
    "browser": ["открой браузер", "запусти интернет", "открой гугл", "вруби зен", "запусти браузер"],
    "search_google": ["найди в гугле", "загугли", "поиск в интернете", "найди информацию"],
    "search_youtube": ["найди на ютубе", "включи на ютубе", "ютуб", "покажи видео", "найди видео"],
    "steam": ["открой стим", "запусти стим", "вруби игры", "стим"],
    "discord": ["открой дискорд", "запусти дискорд", "вруби дискорд", "дискорд"],
    "spotify": ["открой спотифай", "запусти спотифай", "вруби музыку", "спотифай", "с пути фай"],
    "zapret": ["открой запрет", "запусти запрет", "запрет два", "включи обход"],
    "play_pause": ["пауза", "стоп", "останови музыку", "продолжить", "включи музыку", "играй"],
    "next_track": ["следующий трек", "включи следующую", "переключи песню", "дальше", "скип"],
    "prev_track": ["предыдущий трек", "верни обратно", "прошлая песня", "назад"],
    "volume_up": ["громче", "прибавь звук", "увеличь громкость", "сделай громче"],
    "volume_down": ["тише", "убавь звук", "уменьши громкость", "сделай тише"],
    "volume_mute": ["выключи звук", "без звука", "заглуши", "мут"],
    "pc_lock": ["заблокируй", "блок", "заблокируй компьютер", "экран"],
    "pc_sleep": ["спящий режим компьютера", "отбой", "иди спать"],
    "huynia": ["что за хуйня", "это хуйня", "че за хуйня", "полная хуйня", "хуйня"]
}

# ==========================================
# ЖЕЛЕЗНЫЙ КОНТРОЛЬ РЕЧИ И ИИ
# ==========================================
def jarvis_speak(text):
    text = text.strip()
    if not text: return
    clean_text = text.rstrip(".!?, ")
    
    if not clean_text.lower().endswith("сэр"):
        text = clean_text + ", сэр."
    else:
        if text[-1] not in [".", "!", "?"]:
            text += "."
            
    print(f"[Джарвис]: {text}")
    speak(text)
    # НОВОЕ: Отправляем ответ ИИ в интерфейс
    if gui_callback:
        gui_callback(text)
        
    speak(text)

def ask_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    system_prompt = (
        "Ты Джарвис, высокотехнологичный ИИ-дворецкий. "
        "Отвечай на русском языке. Будь краток, вежлив, используй сарказм Тони Старка. "
        "НЕ используй обращение 'сэр' — система добавит его сама."
        "В пример личности возьми J.A.R.V.I.S. из киновселенных marvel, созданный Тони Старком. НЕ забывай, твой создатель - я, а не Тони, обращайся ко мне на сэр"
    )
    full_prompt = f"{system_prompt}\nПользователь: {prompt}\nДжарвис:"
    data = {"model": "qwen2.5:3b", "prompt": full_prompt, "stream": False}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            ans = result.get('response', '').strip()
            
            if ans.lower().startswith("сэр"): ans = ans[3:].strip(" ,.!-")
            elif ans.lower().startswith("да, сэр"): ans = "Да, " + ans[7:].strip(" ,.!-")
                
            if ans: ans = ans[0].upper() + ans[1:]
            return ans
    except Exception:
        return "Мои нейронные связи с локальной моделью нарушены"

def speak_ai_action(action, data=""):
    prompt = f"Пользователь дал команду: {action}. "
    if data: prompt += f"Данные для озвучивания: {data}. "
    prompt += "Подтверди выполнение или красиво озвучь данные в 1 коротком предложении."
    ans = ask_ollama(prompt)
    jarvis_speak(ans)

def get_rss_news(url, limit=2):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        titles = []
        for item in root.findall('.//item')[:limit]:
            titles.append(item.find('title').text)
        return titles
    except Exception as e:
        print(f"Ошибка RSS ({url}): {e}")
        return []

def recognize_cmd(cmd_text):
    best_cmd, max_score = None, 0
    for cmd_id, aliases in COMMANDS.items():
        for alias in aliases:
            score = fuzz.token_set_ratio(cmd_text, alias) 
            if score > max_score: max_score, best_cmd = score, cmd_id
    if max_score >= 70: return best_cmd
    return None

# ==========================================
# ИСПОЛНИТЕЛЬНОЕ ЯДРО
# ==========================================
def execute_command(command, from_telegram=False):
    global jarvis_is_sleeping 
    command = command.lower().strip()
    
    # 1. ОБРАБОТКА ИСТОЧНИКА
    if from_telegram:
        clean_command = command
        jarvis_is_sleeping = False 
        play_activation_sound() 
    else:
        found_wake_word = next((w for w in WAKE_WORDS if w in command), None)
        if not found_wake_word:
            return
            
        clean_command = command.replace(found_wake_word, "").strip()
        
        # 2. ПРОВЕРКА РЕЖИМА ОЖИДАНИЯ
        if jarvis_is_sleeping:
            cmd_intent = recognize_cmd(clean_command)
            if cmd_intent == "jarvis_wake":
                jarvis_is_sleeping = False
                play_activation_sound()
                jarvis_speak("Системы переведены в активный режим. Я снова вас слушаю")
            return 
            
        # 3. ЕСЛИ НЕ СПИТ - РАБОТАЕМ ОБЫЧНО
        play_activation_sound() 
        if not clean_command:
            jarvis_speak("Да?")
            return

    print(f"🧠 Текст запроса: {clean_command}")

    # =======================================================
    # 4. ПРОВЕРКА КАСТОМНЫХ КОМАНД ИЗ ИНТЕРФЕЙСА (config.json)
    # =======================================================
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            custom_commands = config_data.get("commands", {})
            
            for cmd_triggers_str, cmd_path in custom_commands.items():
                # НОВОЕ: Разбиваем строку из интерфейса по запятым и убираем лишние пробелы
                triggers = [t.strip() for t in cmd_triggers_str.split(",")]
                
                # Проверяем каждую фразу отдельно
                for trigger in triggers:
                    if trigger and trigger in clean_command:
                        jarvis_speak(f"Выполняю команду.")
                        try:
                            os.startfile(cmd_path)
                        except Exception as e:
                            jarvis_speak("Не удалось запустить файл по указанному пути.")
                        return # Прерываем функцию, команда выполнена
    except Exception:
        pass # Если файла нет, просто переходим к базовым командам

    # =======================================================
    # 5. БАЗОВЫЕ КОМАНДЫ (Из словаря COMMANDS)
    # =======================================================
    cmd_intent = recognize_cmd(clean_command)
        
    if cmd_intent == "jarvis_sleep":
        jarvis_is_sleeping = True
        jarvis_speak("Перехожу в режим ожидания. Позовите, когда понадоблюсь")
        return

    elif cmd_intent == "jarvis_off":
        jarvis_speak("Отключаю питание всех систем. До свидания")
        os._exit(0) # Мгновенное закрытие всей программы

    elif cmd_intent == "news":
        jarvis_speak("Сканирую информационные сети. Дайте мне пару секунд")
        ru_news = get_rss_news("https://lenta.ru/rss/news", limit=2)
        game_news = get_rss_news("https://stopgame.ru/rss/rss_news.xml", limit=2)
        music_query = urllib.parse.quote("Кишлак OR cupsize OR overtonight")
        music_url = f"https://news.google.com/rss/search?q={music_query}&hl=ru&gl=RU&ceid=RU:ru"
        music_news = get_rss_news(music_url, limit=2)
        all_titles = f"Россия: {ru_news}. Игры: {game_news}. Музыка: {music_news}."
        
        if not ru_news and not game_news:
            jarvis_speak("К сожалению, я не смог подключиться к новостным серверам")
            return
            
        prompt = f"Вот свежие заголовки: {all_titles}. Сделай из них связную саркастичную утреннюю сводку в 3-4 предложениях."
        news_summary = ask_ollama(prompt)
        jarvis_speak(news_summary)

    elif cmd_intent == "search_anime":
        words = clean_command.split()
        query = " ".join([w for w in words if w not in ["включи", "найди", "покажи", "на", "сайте", "аниме", "про", "о", "поиск"]])
        if query:
            encoded_query = urllib.parse.quote(query)
            webbrowser.open(f"https://www.google.com/search?q=site:animeon.ru+{encoded_query}")
            speak_ai_action("найти аниме", f"название: {query}")
        else: speak_ai_action("спросить, какое именно аниме включить")

    elif cmd_intent == "search_movie":
        words = clean_command.split()
        query = " ".join([w for w in words if w not in ["включи", "найди", "покажи", "кино", "фильм", "сериал", "про", "о", "поиск"]])
        if query:
            encoded_query = urllib.parse.quote(query)
            webbrowser.open(f"https://www.kinopoisk.ru/index.php?kp_query={encoded_query}")
            speak_ai_action("искать фильм", f"название: {query}")
        else: speak_ai_action("спросить, какой фильм или сериал включить")
            
    elif cmd_intent == "open_website" or ((clean_command.startswith("открой ") or clean_command.startswith("перейди на ")) and not cmd_intent):
        words = clean_command.split()
        query = " ".join([w for w in words if w not in ["открой", "сайт", "перейди", "на", "страницу", "пожалуйста"]])
        if query:
            encoded_query = urllib.parse.quote(f"!ducky {query}")
            webbrowser.open(f"https://duckduckgo.com/?q={encoded_query}")
            speak_ai_action("открыть сайт", f"название: {query}")
        else: speak_ai_action("спросить, какой именно сайт нужно открыть")

    elif cmd_intent == "time":
        now = datetime.datetime.now()
        speak_ai_action("сообщить текущее время", f"{now.hour} часов {now.minute} минут")
        
    elif cmd_intent == "weather_now":
        try:
            url = "http://wttr.in/?format=%t,+%C"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0', 'Accept-Language': 'ru-RU,ru;q=0.9'})
            with urllib.request.urlopen(req, timeout=3) as response:
                w_text = response.read().decode('utf-8').strip()
            translations = {"Light rain shower": "небольшой дождь", "Light rain": "небольшой дождь", "Partly cloudy": "переменная облачность", "Overcast": "пасмурно", "Clear": "ясно", "Sunny": "солнечно", "Cloudy": "облачно", "Rain": "дождь"}
            for eng, rus in translations.items(): w_text = w_text.replace(eng, rus)
            speak_ai_action("сообщить погоду за окном", w_text)
        except Exception: speak_ai_action("сообщить, что нет связи с метеосервером")

    elif cmd_intent == "weather_tomorrow":
        try:
            url = "http://wttr.in/?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            tomorrow = data['weather'][1]
            min_t = tomorrow['mintempC'].replace("-", "минус ")
            max_t = tomorrow['maxtempC'].replace("-", "минус ")
            speak_ai_action("сообщить прогноз погоды на завтра", f"от {min_t} до {max_t} градусов")
        except Exception: speak_ai_action("сообщить, что сервер прогнозов недоступен")

    elif cmd_intent == "welcome_home":
        welcome_text = ask_ollama("Я вернулся домой. Поприветствуй меня как ИИ-дворецкий в 1-2 предложениях.")
        try: os.startfile("spotify:track:39shmbM242yISyKwCMmR1D") 
        except Exception: pass
        try: os.startfile("steam://open/main") 
        except Exception: pass
        webbrowser.open("https://google.com")
        jarvis_speak(welcome_text)

    elif cmd_intent == "browser":
        webbrowser.open("https://google.com")
        speak_ai_action("открыть браузер")
        
    elif cmd_intent == "search_google":
        query = clean_command.replace("найди в гугле", "").replace("загугли", "").strip()
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            speak_ai_action("выполнить поиск в интернете", f"запрос: {query}")
        else: speak_ai_action("спросить, что именно нужно найти")
            
    elif cmd_intent == "search_youtube":
        query = clean_command.replace("найди на ютубе", "").replace("включи на ютубе", "").strip()
        if query:
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            speak_ai_action("открыть видео на ютубе", f"запрос: {query}")
        else: speak_ai_action("спросить, какое видео нужно найти")
    
    elif cmd_intent == "telegram":
        try: os.startfile("tg://"); speak_ai_action("открыть Телеграм")
        except Exception: pass

    elif cmd_intent == "steam":
        try: os.startfile("steam://open/main"); speak_ai_action("запустить Стим")
        except Exception: pass

    elif cmd_intent == "spotify":
        try: os.startfile("spotify:"); speak_ai_action("запустить Спотифай")
        except Exception: pass

    elif cmd_intent == "play_pause": keyboard.send("play/pause media")
    elif cmd_intent == "next_track": keyboard.send("next track")
    elif cmd_intent == "prev_track": keyboard.send("previous track")

    elif cmd_intent == "volume_up":
        for _ in range(5): keyboard.send("volume up")
        speak_ai_action("немного прибавить громкость компьютера")
        
    elif cmd_intent == "volume_down":
        for _ in range(5): keyboard.send("volume down")
        speak_ai_action("убавить громкость компьютера")
        
    elif cmd_intent == "volume_mute":
        keyboard.send("volume mute")
        speak_ai_action("полностью отключить звук на компьютере")

    elif cmd_intent == "pc_lock":
        speak_ai_action("заблокировать экран компьютера")
        os.system("rundll32.exe user32.dll,LockWorkStation")

    elif cmd_intent == "pc_sleep":
        speak_ai_action("перевести компьютер в спящий режим")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    elif cmd_intent == "huynia":
        jarvis_speak("Я сам в ахуе")
        
    else:
        answer = ask_ollama(clean_command)
        jarvis_speak(answer)

# ==========================================
# ФОНОВЫЙ ПОТОК ТЕЛЕГРАМ-БОТА
# ==========================================
def run_telegram_bot():
    if not TELEGRAM_BOT_TOKEN:
        return 
        
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    print("📱 Telegram-модуль запущен! Ожидаю сообщений...")

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        user_id = str(message.chat.id)
        if TELEGRAM_ALLOWED_ID and user_id != TELEGRAM_ALLOWED_ID:
            bot.reply_to(message, "Отказано в доступе.")
            return

        bot.reply_to(message, "Команда принята. Выполняю, сэр.")
        execute_command(message.text, from_telegram=True)

    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка Telegram-модуля: {e}")
