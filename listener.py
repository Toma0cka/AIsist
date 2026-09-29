import queue
import sounddevice as sd
import vosk
import json
import sys

# 1. Создаем очередь (буфер) для звука. 
# Микрофон записывает звук непрерывно, и мы складываем его сюда, чтобы ничего не потерять.
q = queue.Queue()

# 2. Функция-перехватчик. 
# Она срабатывает автоматически миллисекунда за миллисекундой, пока включен микрофон.
def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata)) # Кладем кусочек звука в очередь

# 3. Главная функция прослушивания
def start_listening(callback_function):
    print("⏳ Загрузка модели языка (может занять 5-10 секунд)...")
    
    # Загружаем ту самую папку "model", которую вы скачали
    model = vosk.Model("model") 
    
    # 16000 Гц - стандартная частота для распознавания речи
    samplerate = 16000 
    
    # Создаем "распознаватель", который знает язык и частоту
    rec = vosk.KaldiRecognizer(model, samplerate)
    
    print("✅ Джарвис готов! Говорите (для остановки нажмите Ctrl+C)...")

    # Включаем микрофон компьютера
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=2,
                           dtype='int16', channels=1, callback=callback):
        
        # Запускаем бесконечный цикл - программа будет работать вечно, пока мы её не выключим
        while True:
            data = q.get() # Берем звук из нашей очереди
            
            # Функция AcceptWaveform проверяет, закончили ли вы фразу (сделали ли паузу)
            if rec.AcceptWaveform(data):
                # Достаем текст из ответа (ответ приходит в формате JSON)
                result = json.loads(rec.Result())
                text = result.get('text', '')
                
                # Если текст не пустой - выводим на экран
                if text:
                    print(f"[Вы сказали]: {text}")
                    callback_function(text)

# 4. Эта строчка запускает код, если мы запускаем именно этот файл
if __name__ == "__main__":
    try:
        start_listening()
    except KeyboardInterrupt:
        # Если вы нажмете Ctrl+C, программа закроется без красных ошибок
        print("\n❌ Слух Джарвиса отключен.")