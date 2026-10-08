"""Utilidades compartidas de SeedProof (sin dependencias del repo hermano)."""
import json
import os
import re
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Términos que delatan opinión, recomendación, especulación o acusación.
# Un reportero cita hechos: si aparecen en el texto generado, se rechaza el
# boletín entero.
BANNED_WORDS = [
    "recomendamos", "recomendable", "deberías", "debería", "debieras",
    "es crítico que", "es fundamental que", "posiblemente", "probablemente",
    "sospechamos", "sospecha", "atribuimos", "atribución", "creemos que",
    "consideramos que", "alarmante", "preocupante", "urgimos", "instamos",
    "en mi opinión", "estafa", "mintió", "mintieron", "engañó", "engañaron",
    "fraude", "farsa", "humo",
]

USER_AGENT = "seedproof-bot/1.0 (+https://github.com/gonzalodiascenzi/seedproof)"


def load_config():
    with open(os.path.join(ROOT, "config.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def call_anthropic(system_prompt, user_payload, model, api_key):
    body = {
        "model": model,
        "max_tokens": 1536,
        "temperature": 0,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ],
    }
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_model_json(response):
    """Saca el texto de la respuesta de Messages API y lo parsea como JSON,
    tolerando que el modelo lo haya envuelto en un bloque ```json."""
    blocks = response.get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)
