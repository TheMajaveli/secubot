"""
OpenAI-based explanation layer for SecuBot scan reports.

Produces concise French summaries suitable for demos and CV use.
"""

from __future__ import annotations

import json
import logging
from typing import Any

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


class Explainer:
    """Wraps the OpenAI client to turn structured reports into prose."""

    def __init__(self) -> None:
        """Create an explainer using current environment configuration."""

        self._settings = get_config()

    def explain_report(self, report: dict[str, Any]) -> str:
        """Generate a French explanation for a scan report.

        Args:
            report: Output of ``WebScanner.run_full_scan`` (JSON-serializable).

        Returns:
            Model-generated explanation, or a placeholder if API is unavailable.
        """

        if not self._settings.openai_api_key.strip():
            return (
                "Explication indisponible : définissez OPENAI_API_KEY dans votre fichier "
                "`.env` pour activer l'analyse par modèle."
            )
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
