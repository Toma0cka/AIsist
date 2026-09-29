import queue
import sounddevice as sd
import vosk
import json
import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
MODEL_PATH = os.path.join(BASE_DIR, "model")

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

# Добавили mic_index (из настроек) и stop_event (сигнал от кнопки ВЫКЛ)
def start_listening(callback_function, mic_index=None, stop_event=None):
    print("⏳ Загрузка модели языка (может занять 5-10 секунд)...")
    try:
        model = vosk.Model(MODEL_PATH) 
    except Exception as e:
        print("❌ ОШИБКА: Папка 'model' не найдена!")
        return

    samplerate = 16000 
    rec = vosk.KaldiRecognizer(model, samplerate)
    
    # Очищаем старые звуки перед новым запуском
    with q.mutex:
        q.queue.clear()

    # Настраиваем аудио-поток
    stream_args = {
        'samplerate': samplerate, 'blocksize': 8000, 
        'dtype': 'int16', 'channels': 1, 'callback': callback
    }
    # Если в настройках выбран конкретный микрофон - используем его
    if mic_index is not None:
        stream_args['device'] = mic_index

    print(f"✅ Микрофон активирован (ID: {mic_index if mic_index is not None else 'По умолчанию'})...")

    try:
        with sd.RawInputStream(**stream_args):
            # Работаем, пока не поступит сигнал об остановке из интерфейса
            while not (stop_event and stop_event.is_set()):
                try:
                    data = q.get(timeout=0.1) # Ждем звук с таймаутом, чтобы проверять кнопку ВЫКЛ
                except queue.Empty:
                    continue
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    
                    if text:
                        print(f"[Вы сказали]: {text}")
                        callback_function(text) # Отправляем текст в мозг и в GUI
    except Exception as e:
        print(f"❌ ОШИБКА МИКРОФОНА: {e}")
