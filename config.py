# config.py
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

@dataclass
class ProcessorConfig:
    base_dir: Path = field(default_factory=Path.cwd)
    
    @property
    def papers_dir(self) -> Path:
        return self.base_dir / 'full_papers'
        
    @property
    def summaries_dir(self) -> Path:
        return self.base_dir / 'paperboi_summaries'
        
    @property
    def metadata_dir(self) -> Path:
        return self.base_dir / 'metadata'
        
    @property
    def errors_dir(self) -> Path:
        return self.base_dir / 'error_log'
        
    @property
    def master_file(self) -> Path:
        return self.metadata_dir / 'all_papers.json'
    
    def create_directories(self):
        """Create all required directories."""
        for dir_path in [self.papers_dir, self.summaries_dir, 
                        self.metadata_dir, self.errors_dir]:
            dir_path.mkdir(exist_ok=True)

@dataclass
class PaperMetadata:
    original_filename: str
    original_url: str
    num_chunks: int
    processing_date: str = field(default_factory=lambda: datetime.now().isoformat())
    title: Optional[str] = None
    doi: Optional[str] = None
    summary_path: Optional[str] = None
    
    def to_dict(self):
        return {k: str(v) if isinstance(v, Path) else v 
                for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

class MetadataManager:
    def __init__(self, metadata_dir: Path):
        self.metadata_dir = metadata_dir
        self.master_file = metadata_dir / 'all_papers.json'
        self._ensure_master_file()
    
    def _ensure_master_file(self):
        if not self.master_file.exists():
            self.save_master({})
    
    def load_master(self) -> dict:
        try:
            return json.loads(self.master_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_master(self, data: dict):
        self.master_file.write_text(json.dumps(data, indent=4))
    
    def save_paper_metadata(self, metadata: PaperMetadata) -> Path:
        # Save individual metadata file
        filename = f"metadata_{metadata.processing_date.replace(':', '-')}.json"
        file_path = self.metadata_dir / filename
        file_path.write_text(json.dumps(metadata.to_dict(), indent=4))
        
        # Update master file
        master_data = self.load_master()
        key = metadata.doi or metadata.original_filename
        master_data[key] = metadata.to_dict()
        self.save_master(master_data)
        
        return file_path

