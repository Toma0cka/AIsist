import asyncio
import edge_tts
import pygame
import os
import winsound

# Инициализация звукового движка pygame
pygame.mixer.init()

# Конфигурация голоса (Ваши настройки)
VOICE = "en-US-BrianMultilingualNeural"
PITCH = "-5Hz"
RATE = "+23%"

TEMP_AUDIO_FILE = "temp_response.mp3"

def play_activation_sound():
    """Короткий высокотехнологичный двойной сигнал отклика"""
    # Частота (Гц), Длительность (мс)
    winsound.Beep(1000, 50)
    winsound.Beep(1600, 80)

async def _synthesize(text: str) -> None:
    """Генерация аудио через облачный сервис Edge"""
    communicate = edge_tts.Communicate(
        text=text, 
        voice=VOICE, 
        pitch=PITCH, 
        rate=RATE
    )
    await communicate.save(TEMP_AUDIO_FILE)

def speak(text: str) -> None:
    """Озвучка текста с автоматическим воспроизведением"""
    print(f"[Джарвис]: {text}")
    try:
        # Синтез аудио через асинхронный таск
        asyncio.run(_synthesize(text))
        
        # Воспроизведение
        pygame.mixer.music.load(TEMP_AUDIO_FILE)
        pygame.mixer.music.play()
        
        # Ожидание окончания реплики
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # Выгрузка файла из памяти для возможности перезаписи
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"Ошибка воспроизведения речи: {e}")
        
    finally:
        if os.path.exists(TEMP_AUDIO_FILE):
            try:
                os.remove(TEMP_AUDIO_FILE)
            except PermissionError:
                pass

if __name__ == "__main__":
    print("Тестирование облачного нейромодуля...")
    play_activation_sound() # Тестируем звук при прямом запуске файла
    speak("Приветствую, сэр. Все системы активны. Протоколы связи с облаком функционируют в штатном режиме.")
