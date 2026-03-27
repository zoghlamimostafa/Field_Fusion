#!/usr/bin/env python3
"""
Lightweight PDF exporter for JSON report files.
Uses matplotlib only, so it works in the current environment without extra packages.
"""

from datetime import datetime
import json
import os
import textwrap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


class PDFReportExporter:
    """Render JSON reports into readable paginated PDF files."""

    REPORT_TITLES = {
        "formations": "Formation Detection Report",
        "fatigue": "Fatigue Analysis Report",
        "pressing": "Pressing Metrics Report",
        "pass_networks": "Pass Network Report",
        "alerts": "Tactical Alerts Report",
        "confidence": "Confidence Scoring Report",
    }

    def __init__(self, line_width: int = 100, lines_per_page: int = 54):
        self.line_width = line_width
        self.lines_per_page = lines_per_page

    def export_report_dicts(self, reports: dict, output_dir: str) -> dict:
        """Export one PDF per report dict into the given directory."""
        os.makedirs(output_dir, exist_ok=True)
        generated_paths = {}

        for key, data in reports.items():
            pdf_path = os.path.join(output_dir, f"{key}.pdf")
            title = self.REPORT_TITLES.get(key, key.replace("_", " ").title())
            self.export_json_to_pdf(data, pdf_path, title)
            generated_paths[key] = pdf_path

        return generated_paths

    def export_json_to_pdf(self, data: dict, pdf_path: str, title: str) -> None:
        """Write a single JSON-like structure to a paginated PDF."""
        lines = self._to_lines(data)
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with PdfPages(pdf_path) as pdf:
            page_number = 1
            for start in range(0, len(lines), self.lines_per_page):
                page_lines = lines[start:start + self.lines_per_page]
                fig = plt.figure(figsize=(8.27, 11.69))
                plt.axis("off")

                fig.text(0.05, 0.975, title, fontsize=14, fontweight="bold", va="top")
                fig.text(0.05, 0.955, f"Generated: {generated_at}", fontsize=8, va="top")
                fig.text(0.95, 0.955, f"Page {page_number}", fontsize=8, va="top", ha="right")

                y = 0.93
                for line in page_lines:
                    fig.text(0.05, y, line, fontsize=7.8, family="monospace", va="top")
                    y -= 0.016

                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
                page_number += 1

    def _to_lines(self, data: dict) -> list[str]:
        """Convert JSON data into wrapped monospace lines."""
        text = json.dumps(data, indent=2, ensure_ascii=False)
        wrapped_lines = []

        for line in text.splitlines():
            if not line:
                wrapped_lines.append("")
                continue

            chunks = textwrap.wrap(
                line,
                width=self.line_width,
                replace_whitespace=False,
                drop_whitespace=False,
                subsequent_indent="  ",
            )
            wrapped_lines.extend(chunks or [""])

        return wrapped_lines or ["{}"]
