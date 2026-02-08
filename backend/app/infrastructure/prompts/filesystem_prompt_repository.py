from hashlib import sha256
from pathlib import Path

from app.application.errors import PromptResolutionError
from app.domain.services.prompt_repository import PromptRepository, PromptTemplate


class FilesystemPromptRepository(PromptRepository):
    def __init__(self, prompts_dir: str | Path) -> None:
        self._prompts_dir = Path(prompts_dir)

    def get(self, prompt_id: str) -> PromptTemplate:
        candidate_paths = [
            self._prompts_dir / f"{prompt_id}.md",
            self._prompts_dir / f"{prompt_id}.txt",
            self._prompts_dir / prompt_id,
        ]

        prompt_path = next((path for path in candidate_paths if path.is_file()), None)
        if prompt_path is None:
            raise PromptResolutionError(f"Prompt not found for id: {prompt_id}")

        content = prompt_path.read_text(encoding="utf-8")
        content_hash = sha256(content.encode("utf-8")).hexdigest()

        return PromptTemplate(
            prompt_id=prompt_id,
            content=content,
            version=content_hash[:12],
            sha256=content_hash,
        )
