import threading
import pymupdf


class TextToSpeechService:
    def __init__(self, editor):
        self.editor = editor
        self._engine = None
        self._is_paused = False
        self._is_speaking = False
        self._speech_thread = None
        self._rate = 150
        self._voice_id = None
        self._init_engine()

    def _init_engine(self):
        """Initialize the TTS engine (pyttsx3 or Windows SAPI fallback)."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
        except ImportError:
            self._engine = None
        except Exception:
            self._engine = None

    def _speak_sync(self, text):
        """Internal synchronous speak method."""
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass
        else:
            try:
                import comtypes.client
                speaker = comtypes.client.CreateObject("SAPI.SpVoice")
                if self._voice_id:
                    speaker.Voice = speaker.GetVoices().Item(self._voice_id)
                speaker.Rate = int((self._rate - 150) / 25)
                speaker.Speak(text)
            except Exception:
                pass
        self._is_speaking = False

    def speak(self, text):
        """Speak the given text aloud in a background thread."""
        if not text:
            return
        self.stop()
        self._is_speaking = True
        self._is_paused = False
        self._speech_thread = threading.Thread(
            target=self._speak_sync, args=(text,), daemon=True
        )
        self._speech_thread.start()

    def speak_page(self, page_num):
        """Extract and speak text from a specific page."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            text = doc[page_num].get_text("text")
            if text.strip():
                self.speak(text)
        except Exception as e:
            raise RuntimeError(f"Cannot read page: {e}")

    def speak_selection(self, text):
        """Speak the given selection text."""
        if text:
            self.speak(text)

    def stop(self):
        """Stop any ongoing speech."""
        self._is_speaking = False
        self._is_paused = False
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        if self._speech_thread and self._speech_thread.is_alive():
            self._speech_thread.join(timeout=1)

    def pause(self):
        """Pause current speech."""
        self._is_paused = True
        if self._engine:
            try:
                self._engine.pause()
            except Exception:
                pass

    def resume(self):
        """Resume paused speech."""
        self._is_paused = False
        if self._engine:
            try:
                self._engine.resume()
            except Exception:
                pass

    def set_rate(self, rate):
        """Set speech rate (words per minute, default 150)."""
        self._rate = max(50, min(300, rate))
        if self._engine:
            try:
                self._engine.setProperty("rate", self._rate)
            except Exception:
                pass

    def set_voice(self, voice_id):
        """Set the voice by ID or index."""
        self._voice_id = voice_id
        if self._engine:
            try:
                voices = self._engine.getProperty("voices")
                if isinstance(voice_id, int) and 0 <= voice_id < len(voices):
                    self._engine.setProperty("voice", voices[voice_id].id)
                elif isinstance(voice_id, str):
                    for v in voices:
                        if v.id == voice_id:
                            self._engine.setProperty("voice", v.id)
                            break
            except Exception:
                pass

    def get_voices(self):
        """Return list of available voices."""
        try:
            if self._engine:
                voices = self._engine.getProperty("voices")
                return [
                    {"id": v.id, "name": v.name}
                    for v in voices
                ]
            try:
                import comtypes.client
                speaker = comtypes.client.CreateObject("SAPI.SpVoice")
                voices = speaker.GetVoices()
                result = []
                for i in range(count := voices.Count):
                    v = voices.Item(i)
                    result.append({
                        "id": str(i),
                        "name": v.GetDescription()
                    })
                return result
            except Exception:
                return []
        except Exception:
            return []
