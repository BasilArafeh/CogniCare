import logging
import math
import os
import re
import struct
import uuid
import wave

import requests
from fastapi import HTTPException, status

from core.config import settings
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

GENERATED_AUDIO_DIR = "generated_audio"
os.makedirs(GENERATED_AUDIO_DIR, exist_ok=True)


def is_tts_mock_mode() -> bool:
    val = os.getenv("SPEECH_MOCK_MODE", "false")
    logger.info("[TTS] SPEECH_MOCK_MODE=%r → mock=%s", val, val.lower() == "true")
    return val.lower() == "true"


def get_patient_stage(patient_id: int) -> str:
    client = get_supabase_client()
    result = (
        client.table("patients")
        .select("diagnosis_stage")
        .eq("patient_id", patient_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return "early"

    return str(result.data[0].get("diagnosis_stage") or "early")


def normalize_patient_stage(stage: str | None) -> str:
    if not stage:
        return "early"

    stage = stage.strip().lower()

    if stage in {"early", "mild"}:
        return "early"
    if stage in {"moderate", "middle", "mid"}:
        return "moderate"
    if stage in {"severe", "late", "advanced"}:
        return "severe"

    return "early"


def normalize_language(language: str | None) -> str:
    if not language:
        return "en"

    language = language.strip().lower()

    if language.startswith("ar"):
        return "ar"

    return "en"


def get_voice_id_for_language(language: str) -> str:
    normalized = normalize_language(language)

    if normalized == "ar":
        voice_id = settings.ELEVENLABS_VOICE_ID_AR or settings.ELEVENLABS_VOICE_ID
        if not voice_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing ELEVENLABS_VOICE_ID_AR (or ELEVENLABS_VOICE_ID) in .env",
            )
        return voice_id

    voice_id = settings.ELEVENLABS_VOICE_ID_EN or settings.ELEVENLABS_VOICE_ID
    if not voice_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_VOICE_ID_EN (or ELEVENLABS_VOICE_ID) in .env",
        )
    return voice_id


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split()).strip()


def add_speech_friendly_punctuation(text: str) -> str:
    text = normalize_whitespace(text)
    text = text.replace(";", ". ")
    text = text.replace(" : ", ". ")
    text = text.replace(" - ", ". ")
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*\.\s*", ". ", text)
    text = re.sub(r"\s*\?\s*", "? ", text)
    text = re.sub(r"\s*!\s*", "! ", text)
    text = normalize_whitespace(text)

    if text and text[-1] not in ".!?":
        text += "."

    return text


def simplify_for_moderate_stage(text: str) -> str:
    text = text.replace("; ", ". ")
    text = text.replace(": ", ". ")
    text = text.replace(" and then ", ". Then ")
    text = text.replace(" then ", ". Then ")
    text = text.replace(", and ", ". ")
    text = text.replace(", but ", ". ")
    return add_speech_friendly_punctuation(text)


def simplify_for_severe_stage(text: str) -> str:
    text = text.replace("; ", ". ")
    text = text.replace(": ", ". ")
    text = text.replace(", and ", ". ")
    text = text.replace(", but ", ". ")
    text = text.replace(" and then ", ". Then ")
    text = text.replace(" then ", ". Then ")
    text = text.replace(", ", ". ")
    return add_speech_friendly_punctuation(text)


def prepare_tts_text(text: str, patient_stage: str | None = None) -> str:
    cleaned = add_speech_friendly_punctuation(text)
    stage = normalize_patient_stage(patient_stage)

    if stage == "moderate":
        return simplify_for_moderate_stage(cleaned)

    if stage == "severe":
        return simplify_for_severe_stage(cleaned)

    return cleaned


def generate_mock_audio_file() -> str:
    file_name = f"{uuid.uuid4()}.wav"
    file_path = os.path.join(GENERATED_AUDIO_DIR, file_name)

    sample_rate = 22050
    duration_seconds = 1.0
    frequency = 440.0
    amplitude = 8000

    with wave.open(file_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        total_frames = int(sample_rate * duration_seconds)

        for i in range(total_frames):
            value = int(amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate)))
            wav_file.writeframesraw(struct.pack("<h", value))

    return file_path


def synthesize_speech(text: str, patient_id: int, language: str) -> str:
    logger.info("[TTS] synthesize_speech called — patient_id=%s language=%s text=%r", patient_id, language, text)

    patient_stage = normalize_patient_stage(get_patient_stage(patient_id))
    logger.info("[TTS] patient_stage=%s", patient_stage)

    cleaned_text = prepare_tts_text(text, patient_stage)
    logger.info("[TTS] cleaned_text=%r", cleaned_text)

    voice_id = get_voice_id_for_language(language)
    logger.info("[TTS] voice_id=%s", voice_id)

    if is_tts_mock_mode():
        logger.info("[TTS] mock mode active — generating beep WAV")
        return generate_mock_audio_file()

    if not settings.ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_API_KEY in .env",
        )

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{voice_id}?output_format=mp3_44100_128"
    )

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": cleaned_text,
        "model_id": "eleven_multilingual_v2",
    }

    logger.info("[TTS] calling ElevenLabs API — voice_id=%s", voice_id)
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
    )
    logger.info("[TTS] ElevenLabs responded — status=%s content_length=%s", response.status_code, len(response.content))

    if response.status_code != 200:
        logger.error("[TTS] ElevenLabs error — %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS failed: {response.text}",
        )

    output_path = os.path.join(GENERATED_AUDIO_DIR, f"{uuid.uuid4()}.mp3")

    with open(output_path, "wb") as audio_file:
        audio_file.write(response.content)

    logger.info("[TTS] MP3 saved to %s (%d bytes)", output_path, len(response.content))
    return output_path


def remove_tts_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)