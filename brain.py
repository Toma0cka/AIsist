import datetime
import webbrowser
import os
import keyboard 
import urllib.request 
import urllib.parse
import json 
import xml.etree.ElementTree as ET 
from rapidfuzz import fuzz
from speaker import speak, play_activation_sound
from listener import start_listening

WAKE_WORDS = ["джарвис", "жарвис", "чарвис", "дарвис", "джервис", "джонс", "завес", "жадность", "джой с", "занавес", "джонас"]

# --- СЛОВАРЬ КОМАНД ---
COMMANDS = {
    "time": ["сколько времени", "который час", "текущее время", "скажи время", "время"],
    "weather_now": ["погода", "какая сейчас погода", "что за окном", "метеосводка"], 
    "weather_tomorrow": ["погода на завтра", "прогноз на завтра", "что будет завтра", "завтра погода"], 
    
    # Расширенный список для новостей
    "news": ["новости", "сводка новостей", "что нового", "утренние новости", "расскажи новости", "что по новостям", "какие новости", "новости на сегодня"],
    
    "welcome_home": ["просыпайся папочка дома", "просыпайся я вернулся", "я дома", "запускай протокол дом", "я вернулся"],
    "browser": ["открой браузер", "запусти интернет", "открой гугл", "вруби зен", "запусти браузер"],
    "search_google": ["найди в гугле", "загугли", "поиск в интернете", "найди информацию"],
    "search_youtube": ["найди на ютубе", "включи на ютубе", "ютуб", "покажи видео", "найди видео"],
    "steam": ["открой стим", "запусти стим", "вруби игры", "стим"],
    "discord": ["открой дискорд", "запусти дискорд", "вруби дискорд", "дискорд", "детскую", "диску от", "эскорт"],
    "spotify": ["открой спотифай", "запусти спотифай", "вруби музыку", "спотифай", "с пути фай"],
    "zapret": ["открой запрет", "запусти запрет", "запрет два", "включи обход"],
    "play_pause": ["пауза", "стоп", "останови музыку", "коч", "продолжить", "включи музыку", "играй"],
    "next_track": ["следующий трек", "включи следующую", "переключи песню", "дальше", "скип"],
    "prev_track": ["предыдущий трек", "верни обратно", "прошлая песня", "назад"],
    "volume_up": ["громче", "прибавь звук", "увеличь громкость", "сделай громче"],
    "volume_down": ["тише", "убавь звук", "уменьши громкость", "сделай тише"],
    "volume_mute": ["выключи звук", "без звука", "заглуши", "мут"],
    "pc_lock": ["заблокируй", "блок", "заблокируй компьютер", "экран"],
    "pc_sleep": ["спящий режим", "режим сна", "отбой", "иди спать"],
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

def ask_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    system_prompt = (
        "Ты Джарвис, высокотехнологичный ИИ-дворецкий. "
        "Отвечай на русском языке. Будь краток, вежлив, используй сарказм Тони Старка. "
        "НЕ используй обращение 'сэр' — система добавит его сама."
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

# ==========================================
# ФУНКЦИЯ СБОРА НОВОСТЕЙ (RSS)
# ==========================================
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

def execute_command(command):
    command = command.lower().strip()
    found_wake_word = next((w for w in WAKE_WORDS if w in command), None)

    if found_wake_word:
        play_activation_sound() 
        clean_command = command.replace(found_wake_word, "").strip()
        
        if not clean_command:
            jarvis_speak("Да?")
            return

        cmd_intent = recognize_cmd(clean_command)
        print(f"🧠 Интент распознан как: {cmd_intent}")
        
        # ==========================================
        # УМНАЯ СВОДКА НОВОСТЕЙ
        # ==========================================
        if cmd_intent == "news":
            jarvis_speak("Сканирую информационные сети. Дайте мне пару секунд")
            
            # 1. Обычные новости
            ru_news = get_rss_news("https://lenta.ru/rss/news", limit=2)
            
            # 2. Игровые новости
            game_news = get_rss_news("https://stopgame.ru/rss/rss_news.xml", limit=2)
            
            # 3. Музыкальные новости (Ваши любимые исполнители)
            my_music = "Кишлак OR cupsize OR overtonight OR lazzy2wice OR урал гайсин OR deathlain OR королевский XVII OR темный принц"
            music_query = urllib.parse.quote(my_music)
            music_url = f"https://news.google.com/rss/search?q={music_query}&hl=ru&gl=RU&ceid=RU:ru"
            music_news = get_rss_news(music_url, limit=2)
            
            all_titles = f"Россия: {ru_news}. Игры: {game_news}. Музыка: {music_news}."
            
            if not ru_news and not game_news:
                jarvis_speak("К сожалению, я не смог подключиться к новостным серверам")
                return
                
            prompt = (
                f"Вот свежие заголовки новостей: {all_titles}. "
                "Сделай из них связную, саркастичную утреннюю сводку новостей. "
                "Расскажи в 3-4 предложениях. Веди себя как Джарвис."
            )
            
            news_summary = ask_ollama(prompt)
            jarvis_speak(news_summary)

        elif cmd_intent == "time":
            now = datetime.datetime.now()
            speak_ai_action("сообщить текущее время", f"{now.hour} часов {now.minute} минут")
            
        elif cmd_intent == "weather_now":
            try:
                url = "http://wttr.in/?format=%t,+%C"
                req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0', 'Accept-Language': 'ru-RU,ru;q=0.9'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    w_text = response.read().decode('utf-8').strip()
                
                translations = {"Light rain shower": "небольшой дождь", "Light rain": "небольшой дождь", "Partly cloudy": "переменная облачность", "Overcast": "пасмурно", "Clear": "ясно", "Sunny": "солнечно", "Cloudy": "облачно", "Rain": "дождь", "Snow": "снег", "Fog": "туман", "Mist": "дымка", "Moderate rain": "умеренный дождь", "Heavy rain": "сильный дождь"}
                for eng, rus in translations.items(): w_text = w_text.replace(eng, rus)
                w_text = w_text.replace("°C", " градусов").replace("+", "плюс ").replace("-", "минус ")
                speak_ai_action("сообщить погоду за окном", w_text)
            except Exception:
                speak_ai_action("сообщить, что нет связи с метеосервером")

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
            except Exception:
                speak_ai_action("сообщить, что сервер прогнозов недоступен")

        elif cmd_intent == "welcome_home":
            welcome_text = ask_ollama("Я вернулся домой. Поприветствуй меня как ИИ-дворецкий в 1-2 предложениях.")
            try: os.startfile("spotify:track:39shmbM242yISyKwCMmR1D") # Убедитесь, что тут ВАШ URI
            except Exception: pass
            try: os.startfile("steam://open/main") 
            except Exception: pass
            try: os.startfile(r"C:\Users\blxnd\AppData\Local\Discord\Discord.exe") 
            except Exception: pass
            webbrowser.open("https://google.com")
            jarvis_speak(welcome_text)

        elif cmd_intent == "browser":
            webbrowser.open("https://google.com")
            speak_ai_action("открыть браузер")
            
        elif cmd_intent == "search_google":
            words = clean_command.split()
            stop_words = ["найди", "найти", "в", "гугле", "гугл", "загугли", "поиск", "интернете", "информацию", "про", "о"]
            query = " ".join([w for w in words if w not in stop_words])
            if query:
                webbrowser.open(f"https://www.google.com/search?q={query}")
                speak_ai_action("выполнить поиск в интернете", f"запрос: {query}")
            else: speak_ai_action("спросить, что именно нужно найти")
                
        elif cmd_intent == "search_youtube":
            words = clean_command.split()
            stop_words = ["найди", "найти", "на", "в", "ютубе", "ютуб", "youtube", "включи", "покажи", "видео", "про", "о"]
            query = " ".join([w for w in words if w not in stop_words])
            if query:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                speak_ai_action("открыть видео на ютубе", f"запрос: {query}")
            else: speak_ai_action("спросить, какое видео нужно найти")
    
        elif cmd_intent == "telegram":
            try: os.startfile("tg://"); speak_ai_action("открыть Телеграм")
            except Exception: speak_ai_action("сообщить, что Телеграм не отвечает")

        elif cmd_intent == "steam":
            try: os.startfile("steam://open/main"); speak_ai_action("запустить Стим")
            except Exception: speak_ai_action("сообщить, что Стим не отвечает")

        elif cmd_intent == "spotify":
            try: os.startfile("spotify:"); speak_ai_action("запустить Спотифай")
            except Exception: speak_ai_action("сообщить, что Спотифай не отвечает")

        elif cmd_intent == "discord":
            try: os.startfile(r"C:\Users\blxnd\AppData\Local\Discord\Discord.exe"); speak_ai_action("открыть Дискорд")
            except Exception: speak_ai_action("сообщить, что Дискорд не найден")

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

if __name__ == "__main__":
    jarvis_speak("Системы онлайн. Ожидаю ваших команд")
    start_listening(execute_command)