"""Protocol/Interface for tool implementations"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from abc import ABC, abstractmethod

@runtime_checkable
class ToolInterface(Protocol):
    """Protocol that all tool implementations must follow"""
    
    tool_id: str
    name: str
    description: str
    capabilities: List[str]
    keywords: List[str]
    
    async def initialize(self) -> bool:
        """Initialize the tool's resources"""
        ...
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given context"""
        ...
    
    def matches_query(self, query: str) -> float:
        """Return confidence score (0-1) that this tool matches the query"""
        ...