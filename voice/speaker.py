import pyttsx3

# Create the engine once
engine = pyttsx3.init("espeak")

engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)


def speak(text):
    try:
        engine.say(str(text))
        engine.runAndWait()

    except Exception as e:
        print("Speech Error:", e)