import os
import io
import wave
import struct
import tempfile
import threading

import pymupdf


class AdvancedTextToSpeechService:
    def __init__(self, editor):
        self.editor = editor
        self._engine = None
        self._is_speaking = False
        self._is_paused = False
        self._speech_thread = None
        self._rate = 150
        self._pitch = 1.0
        self._volume = 1.0
        self._voice_id = None
        self._language = "en"
        self._current_position = 0
        self._bookmarks = []
        self._cancel_event = threading.Event()
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)
            self._pyttsx3_available = True
        except (ImportError, Exception):
            self._engine = None
            self._pyttsx3_available = False

    def speak(self, text):
        if not text or self._is_speaking:
            return
        self._cancel_event.clear()
        self._is_speaking = True
        self._is_paused = False
        self._speech_thread = threading.Thread(target=self._speak_thread, args=(text,), daemon=True)
        self._speech_thread.start()

    def _speak_thread(self, text):
        try:
            if self._pyttsx3_available and self._engine:
                self._engine.setProperty("rate", self._rate)
                self._engine.setProperty("volume", self._volume)
                self._engine.say(text)
                self._engine.runAndWait()
            else:
                self._speak_windows_sapi(text)
        except Exception:
            pass
        finally:
            self._is_speaking = False

    def _speak_windows_sapi(self, text):
        try:
            import comtypes.client
            speaker = comtypes.client.CreateObject("SAPI.SpVoice")
            speaker.Rate = int((self._rate - 150) / 25)
            speaker.Volume = int(self._volume * 100)
            speaker.Speak(text)
        except Exception:
            pass

    def speak_page(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            text = doc[page_num].get_text("text")
            self.speak(text)
        except Exception:
            pass

    def speak_selection(self, text):
        self.speak(text)

    def speak_range(self, start_page, end_page):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            start_page = max(0, start_page)
            end_page = min(len(doc), end_page + 1)
            combined_text = ""
            for pg in range(start_page, end_page):
                page_text = doc[pg].get_text("text")
                if page_text.strip():
                    combined_text += f"Page {pg + 1}. {page_text}\n\n"
            self.speak(combined_text)
        except Exception:
            pass

    def speak_with_bookmarks(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            toc = doc.get_toc()
            text = doc[page_num].get_text("text")
            bookmark_headers = [t[1] for t in toc if t[2] == page_num + 1]
            if bookmark_headers:
                text = f"{bookmark_headers[0]}. {text}"
            self.speak(text)
        except Exception:
            pass

    def pause(self):
        if self._is_speaking and not self._is_paused:
            self._is_paused = True
            if self._pyttsx3_available and self._engine:
                try:
                    self._engine.pause()
                except Exception:
                    pass

    def resume(self):
        if self._is_paused:
            self._is_paused = False
            if self._pyttsx3_available and self._engine:
                try:
                    self._engine.resume()
                except Exception:
                    pass

    def stop(self):
        self._cancel_event.set()
        self._is_speaking = False
        self._is_paused = False
        if self._pyttsx3_available and self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass

    def set_rate(self, rate):
        self._rate = max(50, min(300, rate))
        if self._pyttsx3_available and self._engine:
            try:
                self._engine.setProperty("rate", self._rate)
            except Exception:
                pass

    def set_pitch(self, pitch):
        self._pitch = max(0.5, min(2.0, pitch))

    def set_volume(self, volume):
        self._volume = max(0.0, min(1.0, volume))
        if self._pyttsx3_available and self._engine:
            try:
                self._engine.setProperty("volume", self._volume)
            except Exception:
                pass

    def get_voices(self):
        voices = []
        if self._pyttsx3_available and self._engine:
            try:
                for voice in self._engine.getProperty("voices"):
                    voices.append({
                        "id": voice.id,
                        "name": voice.name,
                        "languages": voice.languages,
                    })
            except Exception:
                pass
        if not voices:
            voices.append({"id": "default", "name": "Default Voice", "languages": ["en"]})
        return voices

    def set_voice(self, voice_id):
        self._voice_id = voice_id
        if self._pyttsx3_available and self._engine:
            try:
                self._engine.setProperty("voice", voice_id)
            except Exception:
                pass

    def detect_language(self, text):
        if not text:
            return "en"
        sample = text[:500]
        lang_hints = {
            "en": ["the", "and", "is", "in", "to", "of", "a", "that", "it", "for"],
            "es": ["el", "la", "los", "las", "de", "en", "que", "por", "con", "una"],
            "fr": ["le", "la", "les", "de", "des", "un", "une", "est", "et", "en"],
            "de": ["der", "die", "das", "und", "ist", "in", "den", "von", "zu", "mit"],
            "it": ["il", "la", "di", "che", "è", "per", "un", "una", "non", "sono"],
            "pt": ["o", "a", "de", "que", "em", "um", "uma", "para", "com", "não"],
            "nl": ["de", "het", "een", "van", "en", "in", "is", "dat", "op", "te"],
            "ru": ["и", "в", "не", "на", "что", "он", "как", "это", "по", "из"],
            "zh": ["的", "是", "在", "不", "了", "有", "和", "人", "这", "中"],
            "ja": ["の", "は", "に", "を", "た", "が", "で", "て", "と", "し"],
            "ko": ["이", "가", "은", "는", "을", "를", "에", "의", "로", "와"],
        }
        lower_sample = sample.lower()
        scores = {}
        for lang, words in lang_hints.items():
            score = sum(1 for w in words if f" {w} " in f" {lower_sample} ")
            scores[lang] = score
        best_lang = max(scores, key=scores.get)
        return best_lang if scores[best_lang] > 0 else "en"

    def export_to_audio(self, text, output_path, format_type="wav", sample_rate=22050):
        if not text:
            return {"success": False, "error": "No text provided"}
        try:
            samples = self._text_to_samples(text, sample_rate)
            if format_type == "wav":
                self._write_wav(output_path, samples, sample_rate)
            else:
                self._write_wav(output_path, samples, sample_rate)
            return {"success": True, "output_path": output_path, "duration_seconds": len(samples) / sample_rate}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _text_to_samples(self, text, sample_rate):
        samples = []
        for char in text:
            if char == ' ':
                period = int(sample_rate * 0.05)
                samples.extend([0] * period)
            elif char == '.':
                period = int(sample_rate * 0.3)
                samples.extend([0] * period)
            elif char == ',':
                period = int(sample_rate * 0.15)
                samples.extend([0] * period)
            elif char == '\n':
                period = int(sample_rate * 0.2)
                samples.extend([0] * period)
            else:
                freq = 200 + (ord(char.lower()) - ord('a')) * 15 if char.isalpha() else 150
                freq *= self._pitch
                period = int(sample_rate * 0.03)
                for i in range(period):
                    t = i / sample_rate
                    sample = int(16000 * self._volume * __import__('math').sin(2 * 3.14159 * freq * t))
                    samples.append(max(-32768, min(32767, sample)))
        return samples

    def _write_wav(self, path, samples, sample_rate):
        with wave.open(path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for s in samples:
                wav_file.writeframes(struct.pack('<h', max(-32768, min(32767, s))))

    def export_page_audio(self, page_num, output_path, format_type="wav"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            text = doc[page_num].get_text("text")
            return self.export_to_audio(text, output_path, format_type)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_speaking(self):
        return self._is_speaking

    def is_paused(self):
        return self._is_paused

    def get_status(self):
        return {
            "speaking": self._is_speaking,
            "paused": self._is_paused,
            "rate": self._rate,
            "volume": self._volume,
            "pitch": self._pitch,
            "voice_id": self._voice_id,
        }
