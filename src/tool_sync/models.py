from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass
class WorkItem:
    id: int
    type: str
    title: str
    state: str
    description: str
    created_date: datetime
    changed_date: datetime
    fields: Dict[str, Any] = field(default_factory=dict)
    local_path: str = ""
    content_hash: str = ""
    last_sync_date: datetime = None
