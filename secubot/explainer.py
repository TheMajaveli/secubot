"""
LLM explanation layer for SecuBot scan reports (Anthropic or OpenAI).

Produces concise French summaries suitable for demos and CV use.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from openai import OpenAI

from secubot.utils import get_config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Tu es un expert en cybersécurité applicative. \n"
    "On te donne un rapport de scan automatique d'un site web.\n"
    "Explique les vulnérabilités trouvées en langage clair, sans jargon excessif.\n"
    "Pour chaque problème détecté, donne : le risque, l'impact potentiel, et une recommandation concrète.\n"
    "Sois concis — maximum 400 mots. Réponds en français."
)

_NO_KEY_MESSAGE = (
    "Explication indisponible : définissez ANTHROPIC_API_KEY ou OPENAI_API_KEY dans `.env` "
    "pour activer l'analyse par modèle."
)


class Explainer:
    """Turns structured scan reports into French prose via Anthropic (preferred) or OpenAI."""

    def __init__(self) -> None:
        """Create an explainer using current environment configuration."""

        self._settings = get_config()

    def explain_report(self, report: dict[str, Any]) -> str:
        """Generate a French explanation for a scan report.

        Args:
            report: Output of ``WebScanner.run_full_scan`` (JSON-serializable).

        Returns:
            Model-generated explanation, or a placeholder if no provider is configured.
        """

        if self._settings.anthropic_api_key.strip():
            return self._explain_anthropic(report)
        if self._settings.openai_api_key.strip():
            return self._explain_openai(report)
        return _NO_KEY_MESSAGE

    def _explain_anthropic(self, report: dict[str, Any]) -> str:
        """Call Anthropic Messages API (default: small Haiku for low cost)."""

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        user_payload = json.dumps(report, ensure_ascii=False)
        try:
            msg = client.messages.create(
                model=self._settings.anthropic_model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_payload}],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic explain failed: %s", str(exc))
            return (
                "Impossible de générer l'explication pour le moment. "
                "Vérifiez votre clé API et le nom du modèle, puis réessayez."
            )
        for block in msg.content:
            if block.type == "text":
                return (block.text or "").strip()
        return ""

    def _explain_openai(self, report: dict[str, Any]) -> str:
        """Call OpenAI Chat Completions (legacy path)."""

        client = OpenAI(api_key=self._settings.openai_api_key)
        try:
            completion = client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(report, ensure_ascii=False),
                    },
                ],
                temperature=0.3,
            )
            choice = completion.choices[0].message.content
            return (choice or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI explain failed: %s", str(exc))
            return (
                "Impossible de générer l'explication pour le moment. "
                "Vérifiez votre clé API et réessayez plus tard."
            )
