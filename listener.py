import queue
import sounddevice as sd
import vosk
import json
import sys

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def start_listening(callback_function):
    print("⏳ Загрузка модели языка (может занять 5-10 секунд)...")
    try:
        model = vosk.Model("model") 
    except Exception as e:
        print(f"❌ ОШИБКА: Папка 'model' не найдена! Убедитесь, что скачали модель Vosk. {e}")
        return

    samplerate = 16000 
    rec = vosk.KaldiRecognizer(model, samplerate)
    
    print("✅ Джарвис готов! Говорите (для остановки нажмите Ctrl+C)...")

    # УБРАЛ ЖЕСТКИЙ DEVICE=2! ТЕПЕРЬ ИСПОЛЬЗУЕТСЯ МИКРОФОН ПО УМОЛЧАНИЮ
    try:
        with sd.RawInputStream(samplerate=samplerate, blocksize=8000, 
                               dtype='int16', channels=1, callback=callback):
            while True:
                data = q.get() 
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    
                    if text:
                        print(f"[Вы сказали]: {text}")
                        callback_function(text)
    except Exception as e:
        print(f"❌ ОШИБКА МИКРОФОНА: Настройте микрофон по умолчанию в Windows! Подробности: {e}")

if __name__ == "__main__":
    try:
        # Для теста просто печатаем текст
        start_listening(print)
    except KeyboardInterrupt:
        print("\n❌ Слух Джарвиса отключен.")
