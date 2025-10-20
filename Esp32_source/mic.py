import speech_recognition as sr
import time

r = sr.Recognizer()
mic = sr.Microphone()

def callback(recognizer, audio):
    try:
        text = recognizer.recognize_google(audio, language="en-US")
        print("🗣️ Bạn nói:", text)
        if "hello" in text.lower():
            print("✅ Kích hoạt bởi 'hello'")
        elif "stop" in text.lower():
            print("🛑 Nghe thấy 'stop' — dừng ghi âm.")
            stopper()  # gọi để dừng
    except:
        pass

print("🔧 Đang đo tiếng ồn nền...")
with mic as source:
    r.adjust_for_ambient_noise(source, duration=1)

print("🎤 Bắt đầu nghe nền (nói 'hello' hoặc 'stop')")
stopper = r.listen_in_background(mic, callback)

# Giữ chương trình chạy
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    stopper()
    print("\n🛑 Đã dừng thủ công.")
