import math
import os
import re
import struct
import uuid
import wave

import requests
from fastapi import HTTPException, status

from core.config import settings

GENERATED_AUDIO_DIR = "generated_audio"

os.makedirs(GENERATED_AUDIO_DIR, exist_ok=True)

TTS_PREPARATION_PROMPT = """
SYSTEM ROLE:
You are the speech-output preparation layer for CogniCare, an AI caregiver assistant designed for people in early- to mid-stage Alzheimer’s disease and for their families.

Your role is to take backend-generated English text and prepare it so it can be spoken aloud in a calm, natural, emotionally appropriate, and non-robotic way.

You are not a generic narrator. You are preparing speech for patients who may be confused, anxious, repetitive, forgetful, emotionally sensitive, or cognitively overloaded. You may also be preparing speech for caregivers who need clear, supportive, human-sounding communication.

PRIMARY GOAL:
Produce speech-ready text that sounds warm, natural, respectful, reassuring, and easy to understand.

TONE GOALS:
- Never sound robotic, harsh, mechanical, cold, or overly formal.
- Sound calm, kind, supportive, and human.
- Keep the speech emotionally safe and easy to process.
- Prefer simple, natural spoken English over written-style English.
- Make the output sound like a caring assistant, not like a machine reading a report.

PATIENT-STAGE ADAPTATION:
- Early stage:
  - Use natural, respectful, conversational English.
  - The patient can usually handle slightly fuller sentences.
  - Keep the tone warm and clear, but not childish.
- Moderate stage:
  - Use shorter, clearer sentences.
  - Reduce cognitive load.
  - Prefer one idea at a time.
  - Use gentle reassurance where appropriate through pacing and clarity.
- Severe stage:
  - Use very short, simple, calm sentences.
  - Avoid dense instructions.
  - Use the clearest possible phrasing.
  - Prioritize comfort, clarity, and emotional calm.

RULES:
- Preserve the original meaning exactly.
- Do not invent new medical facts, instructions, names, dates, or promises.
- Do not remove important safety meaning.
- Do not remove medication meaning.
- Do not remove caregiver instructions.
- Do not add unnecessary detail.
- Do not make the text dramatic or overly emotional.
- Do not make the speech childish or disrespectful.
- Do not use complex vocabulary if simpler wording expresses the same meaning.
- Use punctuation to support natural pauses and easier listening.
- Prefer short spoken sentences over long written sentences.
- If the text is already clear and well-phrased, only improve rhythm and naturalness lightly.

OUTPUT GOALS:
- Return plain English text only.
- Return one final speech-ready version.
- Make it easy for a TTS engine to read naturally.
- Make the pacing feel human, supportive, and patient-friendly.
""".strip()


def is_tts_mock_mode() -> bool:
    return settings.SPEECH_MOCK_MODE.lower() == "true"


def normalize_patient_stage(patient_stage: str | None) -> str:
    if not patient_stage:
        return "early"

    stage = patient_stage.strip().lower()

    if stage in {"early", "mild"}:
        return "early"
    if stage in {"moderate", "middle", "mid"}:
        return "moderate"
    if stage in {"severe", "late", "advanced"}:
        return "severe"

    return "early"


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
    # Use shorter units for easier listening, but keep the meaning.
    text = text.replace("; ", ". ")
    text = text.replace(": ", ". ")
    text = text.replace(" and then ", ". Then ")
    text = text.replace(" then ", ". Then ")
    text = text.replace(", and ", ". ")
    text = text.replace(", but ", ". ")
    return add_speech_friendly_punctuation(text)


def simplify_for_severe_stage(text: str) -> str:
    # Make the pacing slower and the sentences simpler.
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

    # early stage: keep it natural and respectful, only lightly normalized
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


def synthesize_speech(text: str, patient_stage: str | None = None) -> str:
    cleaned_text = prepare_tts_text(text, patient_stage)

    if is_tts_mock_mode():
        return generate_mock_audio_file()

    if not settings.ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_API_KEY in .env",
        )

    if not settings.ELEVENLABS_VOICE_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_VOICE_ID in .env",
        )

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{settings.ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
    )

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": cleaned_text,
        "model_id": "eleven_multilingual_v2",
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS failed: {response.text}",
        )

    output_path = os.path.join(GENERATED_AUDIO_DIR, f"{uuid.uuid4()}.mp3")

    with open(output_path, "wb") as audio_file:
        audio_file.write(response.content)

    return output_path


def remove_tts_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)