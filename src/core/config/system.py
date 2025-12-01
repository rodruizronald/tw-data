
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PathsConfig:
    """Configuration for file paths."""

    prompts_dir: Path
    companies_file: Path
    technologies_file: Path
    project_root: Path = field(default_factory=lambda: Path.cwd())

    def initialize_paths(self) -> None:
        """Convert relative paths to absolute paths using project_root."""
        self.prompts_dir = self.project_root / self.prompts_dir
        self.companies_file = self.project_root / self.companies_file
        self.technologies_file = self.project_root / self.technologies_file
