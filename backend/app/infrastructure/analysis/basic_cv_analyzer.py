from pathlib import Path
import re


class BasicCVAnalyzer:
    def analyze(self, file_path: Path) -> dict[str, int]:
        data = file_path.read_bytes()
        text = data.decode("utf-8", errors="ignore")

        words = re.findall(r"\b\w+\b", text)
        lines = [line for line in text.splitlines() if line.strip()]
        email_matches = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

        return {
            "characters": len(text),
            "words": len(words),
            "non_empty_lines": len(lines),
            "emails_detected": len(email_matches),
        }
