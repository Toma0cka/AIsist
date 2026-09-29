import asyncio
import edge_tts
import os
import winsound
import ctypes # ДЛЯ ПРЯМОГО ВОСПРОИЗВЕДЕНИЯ В WINDOWS

VOICE = "en-US-BrianMultilingualNeural"
PITCH = "-5Hz"
RATE = "+23%"
TEMP_AUDIO_FILE = "temp_response.mp3"

def play_activation_sound():
    winsound.Beep(1000, 50)
    winsound.Beep(1600, 80)

async def _synthesize(text: str) -> None:
    communicate = edge_tts.Communicate(
        text=text, 
        voice=VOICE, 
        pitch=PITCH, 
        rate=RATE
    )
    await communicate.save(TEMP_AUDIO_FILE)

def play_audio_windows(filename):
    """Надежное воспроизведение звука средствами самой Windows"""
    try:
        # Команда системному плееру Windows проиграть файл, дождаться конца и закрыться
        command = f'open "{filename}" alias temp_audio'
        ctypes.windll.winmm.mciSendStringW(command, None, 0, None)
        ctypes.windll.winmm.mciSendStringW("play temp_audio wait", None, 0, None)
        ctypes.windll.winmm.mciSendStringW("close temp_audio", None, 0, None)
    except Exception as e:
        print(f"Ошибка плеера Windows: {e}")

def speak(text: str) -> None:
    print(f"[Джарвис]: {text}")
    try:
        # 1. Генерируем mp3
        asyncio.run(_synthesize(text))
        
        # 2. Надежно проигрываем через Windows
        play_audio_windows(TEMP_AUDIO_FILE)
        
    except Exception as e:
        print(f"Ошибка генерации речи: {e}")
        
    finally:
        # 3. Удаляем файл после использования
        if os.path.exists(TEMP_AUDIO_FILE):
            try:
                os.remove(TEMP_AUDIO_FILE)
            except PermissionError:
                pass

if __name__ == "__main__":
    print("Тестирование облачного нейромодуля...")
    play_activation_sound()
    speak("Приветствую, сэр. Все системы активны.")
