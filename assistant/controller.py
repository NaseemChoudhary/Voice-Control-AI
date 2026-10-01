"""Coordinate voice/text commands and publish dashboard events."""

import json
import logging
import threading
from datetime import datetime, timezone

import config
from ai import provider
from commands import weather
from voice import listener, speaker
from assistant.router import route_command
from assistant.intent import classify
from voice.listener import listen, setup_microphone
from voice.speaker import speak

logger = logging.getLogger(__name__)
ACTIVITY_FILE = config.DATA_DIR / "activity.json"
MICROPHONE_STATUS = "Not started"


def _timestamp():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class AssistantController:
    def __init__(self, publish):
        self.publish = publish
        self._stop = threading.Event()
        self._command_lock = threading.Lock()
        self.voice_thread = None
        self.voice_active = False

    def _emit(self, event_type, **data):
        self.publish({"type": event_type, **data})

    def _record_activity(self, command, result, kind="command"):
        entry = {"time": _timestamp(), "kind": kind, "command": command, "result": result}
        try:
            ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
            try:
                with ACTIVITY_FILE.open("r", encoding="utf-8") as activity_file:
                    entries = json.load(activity_file)
                if not isinstance(entries, list):
                    entries = []
            except FileNotFoundError:
                entries = []
            entries.append(entry)
            with ACTIVITY_FILE.open("w", encoding="utf-8") as activity_file:
                json.dump(entries[-250:], activity_file, indent=2)
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not save activity history")
        self._emit("activity", entry=entry)

    def execute(self, command, source="text"):
        command = command.strip()
        if not command:
            return
        with self._command_lock:
            self._emit("message", role="user", text=command, time=_timestamp())
            self._emit("status", text="Thinking…")
            self._emit("assistant_state", state="processing")
            keep_running = True
            try:
                intent = classify(command)
                if intent == "new_chat":
                    self._emit("clear_conversation")
                handled, message, keep_running = route_command(command)
                if not handled:
                    message = "I couldn't identify that command."
                message = message or "Done."
            except Exception:
                logger.exception("Command handling failed")
                intent = locals().get("intent", "")
                message = "Sorry, I couldn't complete that command."

            active_provider = provider.ACTIVE_PROVIDER if intent == "ai" else None
            if intent == "ai":
                self._emit("provider", name=active_provider or "Unavailable")
            is_ai_unavailable = intent == "ai" and active_provider is None
            is_error = is_ai_unavailable or message.lower().startswith("sorry") or "API key is missing" in message
            role = "error" if is_error else "assistant"
            details = "Both AI providers failed. Check the connection and API keys." if is_ai_unavailable else None
            self._emit("message", role=role, text=message, time=_timestamp(),
                       provider=active_provider, details=details)
            self._record_activity(command, message, kind=source)
            if source in {"voice", "dashboard"} and config.SPEECH_ENABLED:
                self._emit("assistant_state", state="speaking")
                speak(message)
            self._emit("assistant_state", state="error" if is_error else "ready")
            self._emit("status", text="Service unavailable" if is_error else ("Ready" if keep_running else "Shutting down"))
            return keep_running

    def start_voice(self):
        if self.voice_thread and self.voice_thread.is_alive():
            return
        self._stop.clear()
        self.voice_thread = threading.Thread(target=self._voice_loop, name="jarvis-voice", daemon=True)
        self.voice_thread.start()

    def stop_voice(self):
        global MICROPHONE_STATUS
        self._stop.set()
        self.voice_active = False
        MICROPHONE_STATUS = "Paused"
        self._emit("diagnostic", key="Microphone", value=MICROPHONE_STATUS)
        self._emit("voice", active=False)
        self._emit("status", text="Voice paused")

    def _voice_loop(self):
        global MICROPHONE_STATUS
        microphone = setup_microphone()
        if microphone is None:
            MICROPHONE_STATUS = "Unavailable"
            self._emit("diagnostic", key="Microphone", value=MICROPHONE_STATUS)
            self._emit("assistant_state", state="error", detail="microphone")
            self._emit("status", text="Microphone unavailable")
            return
        self.voice_active = True
        MICROPHONE_STATUS = "Ready"
        self._emit("voice", active=True)
        self._emit("diagnostic", key="Microphone", value=MICROPHONE_STATUS)
        self._emit("assistant_state", state="listening")
        self._emit("status", text="Listening for “Jarvis”")
        recognition_status = None
        while not self._stop.is_set():
            self._emit("assistant_state", state="listening")
            phrase = listen(microphone, timeout=3, phrase_time_limit=7)
            if listener.RECOGNITION_STATUS != recognition_status:
                recognition_status = listener.RECOGNITION_STATUS
                self._emit("diagnostic", key="Speech Recognition", value=recognition_status)
            if not phrase:
                continue
            normalized = phrase.lower().strip()
            if normalized == "shutdown" or normalized.endswith(" shutdown"):
                self._emit("transcription", text=normalized)
                self.execute("shutdown", source="voice")
                self._stop.set()
                break
            if "jarvis" not in normalized:
                continue
            command = normalized.replace("jarvis", "", 1).strip()
            if not command:
                self._emit("status", text="Listening for your command")
                command = listen(microphone, timeout=8, phrase_time_limit=10)
            if command:
                self._emit("transcription", text=command)
                if self.execute(command, source="voice") is False:
                    self._stop.set()
                    break
        self.voice_active = False
        MICROPHONE_STATUS = "Paused"
        self._emit("diagnostic", key="Microphone", value=MICROPHONE_STATUS)
        self._emit("voice", active=False)
        self._emit("status", text="Voice paused")

    @staticmethod
    def diagnostics():
        try:
            history_size = config.HISTORY_FILE.stat().st_size
            history_state = f"Available · {history_size:,} bytes"
        except FileNotFoundError:
            history_state = "No saved conversation yet"
        except OSError:
            history_state = "Could not read history"
        return {
            "Microphone": MICROPHONE_STATUS if config.MICROPHONE_INDEX >= 0 else "Not configured",
            "Speech Recognition": listener.RECOGNITION_STATUS,
            "Speech Output": "Disabled" if not config.SPEECH_ENABLED else speaker.SPEECH_STATUS,
            "Internet": provider.NETWORK_STATUS,
            "Gemini": provider.GEMINI_STATUS,
            "Groq": provider.GROQ_STATUS,
            "Weather API": weather.WEATHER_STATUS,
            "Conversation Memory": "Active" if history_state.startswith("Available") else "Ready",
            "Conversation store": history_state,
        }
