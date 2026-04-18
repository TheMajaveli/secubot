#!/usr/bin/env python3
"""CLI entrypoint for SecuBot scans (rich output, optional JSON and LLM)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rich.console import Console
from rich.table import Table

from secubot.explainer import Explainer
from secubot.scanner import WebScanner
from secubot.utils import setup_logging, validate_url

console = Console()


def _build_table(report: dict[str, Any]) -> Table:
    """Render scan report as a Rich table."""

    table = Table(title="SecuBot report")
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="magenta")
    for name, data in report.get("headers", {}).items():
        present = data.get("present")
        val = data.get("value") or ""
        status = "present" if present else "missing"
        color = "green" if present else "red"
        table.add_row(name, f"[{color}]{status}[/{color}] {val[:40]}")
    table.add_row("risk_score", str(report.get("risk_score")))
    return table


async def _run(url: str, explain: bool, as_json: bool) -> None:
    validate_url(url)
    scanner = WebScanner()
    report = await scanner.run_full_scan(url)
    if as_json:
        out = dict(report)
        if explain:
            out["explanation"] = Explainer().explain_report(dict(report))
        console.print_json(data=out)
        return
    console.print(_build_table(report))
    if explain:
        console.print("\n[bold]Explanation[/bold]\n")
        console.print(Explainer().explain_report(dict(report)))


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="SecuBot CLI scanner")
    parser.add_argument("url", help="Target https:// URL")
    parser.add_argument("--explain", action="store_true", help="Include LLM explanation (French)")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON")
    args = parser.parse_args()
    try:
        validate_url(args.url)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    try:
        asyncio.run(_run(args.url, args.explain, args.json))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
