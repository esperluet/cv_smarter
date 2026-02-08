from pathlib import Path
from typing import Protocol


class CVAnalyzer(Protocol):
    def analyze(self, file_path: Path) -> dict[str, int]:
        """Analyze a CV file and return aggregate metrics."""
