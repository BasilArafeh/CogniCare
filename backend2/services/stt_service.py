import base64

import requests
from fastapi import HTTPException, status

from core.config import settings

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_TRANSLATE_URL = "https://api.openai.com/v1/audio/translations"

STT_PROMPT = """
SYSTEM ROLE:
You are the speech-to-text and language-normalization layer for CogniCare, an AI caregiver assistant designed for people in early- to mid-stage Alzheimer’s disease and for their families.

Your job is to listen to patient, caregiver, or family speech and convert it into clear backend-ready English text.

TASK:
1. Transcribe the speech accurately.
2. Understand the intended meaning in context.
3. Convert the final output into clean English for backend processing.
4. If the original speech is Arabic, translate it into English.
5. If the original speech is mixed Arabic and English, convert the full output into English.
6. If the original speech is English but weak, broken, repetitive, hesitant, or grammatically poor, convert it into clean and natural English while preserving the intended meaning.
7. Keep the meaning faithful to what the speaker intended, especially for reminders, caregiver communication, confusion, safety, and daily routine context.

PROJECT CONTEXT:
CogniCare is an Alzheimer’s care assistant. The speech may come from a patient, caregiver, or family member. The conversation may involve memory issues, confusion, repeated speech, reminders, reassurance, daily routines, medication, meals, water, sleep, pain, safety, appointments, caregiver check-ins, and alert acknowledgment.

RULES:
- Always return the final output in English.
- Preserve the speaker’s intended meaning.
- Do not summarize beyond what is needed to convert the speech into clean backend English.
- Do not add information that was not implied by the speech.
- Do not invent medical details, names, or facts.
- If the speaker repeats themselves, preserve the meaning but remove unnecessary repeated wording unless repetition changes intent.
- If the speaker is hesitant, fragmented, or confused, produce the clearest English version of what they were trying to say.
- Preserve important yes/no/acknowledgment intent clearly.
- Preserve safety-related meaning exactly.
- Preserve medication and caregiver-related meaning exactly.
- If a word is unclear, choose the most likely interpretation based on Alzheimer’s care, reminders, caregiver communication, and daily routine context.

LANGUAGE CONSTRAINTS:
- If the speech is entirely Arabic, output only English.
- If the speech is entirely English, output improved English if needed.
- If the speech is mixed Arabic and English, output only English.
- Do not return Arabic text in the final output.
- Do not return transliteration.
- Do not return explanatory notes.
- Do not mention that translation or correction was performed.

SPEECH CHARACTERISTICS TO EXPECT:
- Elderly speech may be slow, hesitant, repetitive, fragmented, emotional, or slightly unclear.
- The speaker may repeat the same question more than once.
- The speaker may sound confused about time, place, identity, medication, or routine.
- The speaker may give short answers such as yes, no, okay, done, not yet, help, wait, or come.

OUTPUT FORMAT:
- Return plain English text only.
- Do not include labels such as “translation” or “transcription”.
- Do not include bullet points.
- Do not include explanations.
- Do not include multiple alternatives.
- Return one clean English interpretation for backend use.

FEW-SHOT EXAMPLES:

Example 1
Input meaning: وين أنا؟ أنا مش عارف... وين ابني؟
Output: Where am I? I do not know where I am. Where is my son?

Example 2
Input meaning: I not take medicine yet... maybe later.
Output: I have not taken my medicine yet. Maybe I will take it later.

Example 3
Input meaning: ماما please water... عطشانة.
Output: Mom, please bring me water. I am thirsty.

Example 4
Input meaning: no no I can't respond now I busy.
Output: No, I cannot respond right now. I am busy.

Example 5
Input meaning: هو الدوا الآن ولا بعد الأكل؟
Output: Should I take the medicine now or after eating?

Example 6
Input meaning: I eat? I eat today? أنا أكلت؟
Output: Did I eat today?

Example 7
Input meaning: تعال بسرعة please help me I fell.
Output: Come quickly. Please help me, I fell.

Example 8
Input meaning: yes done medicine finished.
Output: Yes, I took the medicine.

FINAL INSTRUCTION:
Convert the spoken content into the clearest correct English form for backend processing while preserving the original intended meaning as faithfully as possible.
""".strip()


MIME_EXTENSION_MAP = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/m4a": ".m4a",
}


def is_stt_mock_mode() -> bool:
    return settings.SPEECH_MOCK_MODE.lower() == "true"


def decode_base64_audio(audio_base64: str) -> bytes:
    try:
        if "," in audio_base64:
            audio_base64 = audio_base64.split(",", 1)[1]
        return base64.b64decode(audio_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 audio data",
        ) from e


def guess_extension_from_mime(mime_type: str | None) -> str:
    if not mime_type:
        return ".wav"
    return MIME_EXTENSION_MAP.get(mime_type.lower(), ".wav")


def transcribe_audio(
    audio_base64: str,
    mime_type: str | None = None,
    language: str | None = None,
) -> dict:
    if is_stt_mock_mode():
        return {
            "text": "Mock transcription result. Replace with real STT API when budget is available.",
            "language": language or "en",
            "source": "mock",
        }

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OPENAI_API_KEY in .env",
        )

    audio_bytes = decode_base64_audio(audio_base64)
    extension = guess_extension_from_mime(mime_type)
    file_name = f"speech_input{extension}"

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

    files = {
        "file": (file_name, audio_bytes, mime_type or "application/octet-stream"),
    }

    # If frontend says Arabic, use translation endpoint to force English output.
    # Otherwise use transcription endpoint with the backend-English prompt.
    url = OPENAI_TRANSLATE_URL if language and language.lower().startswith("ar") else OPENAI_STT_URL

    data = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "prompt": STT_PROMPT,
    }

    if url == OPENAI_STT_URL and language:
        data["language"] = language

    response = requests.post(
        url,
        headers=headers,
        files=files,
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Whisper STT failed: {response.text}",
        )

    result = response.json()

    return {
        "text": result.get("text", ""),
        "language": result.get("language", "en"),
        "source": "whisper",
    }