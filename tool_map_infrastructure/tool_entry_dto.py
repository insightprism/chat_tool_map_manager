#!/usr/bin/env python3
"""
ToolEntryDTO - Lightweight data structure for tool agents

This module defines the ToolEntryDTO dataclass which represents each tool
in the ToolMapManager. Unlike PersonaEntryDTO which has 40+ fields for
conversation tracking, ToolEntryDTO only contains what tools actually need.

Tools are stateless, one-shot executors that don't maintain conversation history.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolStatusENUM(Enum):
    """Status states for a tool in the system"""
    UNINITIALIZED = "uninitialized"  # Not yet initialized
    READY = "ready"                   # Initialized and ready to use
    EXECUTING = "executing"           # Currently executing
    ERROR = "error"                   # Failed to initialize or errored
    DISABLED = "disabled"             # Temporarily disabled


@dataclass
class ToolEntryDTO:
    """
    Lightweight data structure for tools in the map.
    
    This is a simplified version of PersonaEntryDTO, containing only
    what tools need. Tools don't have conversation history, prompt tracking,
    or other conversational features that personas have.
    """
    
    # ============= Required Fields (no defaults) =============
    tool_id: str                      # Unique identifier for this tool
    tool_instance: Any                # JsonToolAgent instance
    
    # ============= Core Identification (with defaults) =============
    name: str = ""                    # Display name (e.g., "Cost Estimator")
    description: str = ""             # Brief description of the tool
    category: str = "tool"            # Category (always "tool" for tools)
    
    # ============= Tool Configuration =============
    handler_name: str = ""            # Handler for processing (e.g., "pm_image_analysis_handler_async")
    llm_config: Dict[str, Any] = field(default_factory=dict)  # LLM configuration
    system_prompt: str = ""           # System prompt for the tool
    
    # ============= Capabilities & Keywords =============
    capabilities: List[str] = field(default_factory=list)  # What this tool can do
    keywords: List[str] = field(default_factory=list)      # Keywords for matching
    
    # ============= Status Tracking =============
    status: ToolStatusENUM = ToolStatusENUM.UNINITIALIZED
    initialized_at: Optional[datetime] = None
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    total_execution_time: float = 0.0  # Total time spent executing (seconds)
    average_execution_time: float = 0.0  # Average execution time
    
    # ============= Execution History (Limited) =============
    # Tools don't need full conversation history, just recent executions
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_size: int = 50  # Much smaller than personas (they have 100+)
    
    # ============= Error Tracking =============
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # ============= Metadata =============
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate fields after initialization"""
        if not self.tool_id:
            raise ValueError("tool_id is required")
        if not self.tool_instance:
            logger.warning(f"Tool {self.tool_id} initialized without instance")
    
    def update_execution_stats(self, execution_time: float):
        """Update execution statistics after a tool run"""
        self.last_executed = datetime.now()
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.average_execution_time = self.total_execution_time / self.execution_count
    
    def add_to_execution_history(self, entry: Dict[str, Any]):
        """
        Add an execution entry to history.
        
        Args:
            entry: Dictionary containing execution details like:
                   - query: The input query
                   - result: The execution result
                   - success: Whether execution succeeded
                   - execution_time: Time taken
                   - timestamp: When it was executed
        """
        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
        
        self.execution_history.append(entry)
        
        # Trim history if it exceeds max size
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
    
    def record_error(self, error: str):
        """Record an error occurrence"""
        self.error_count += 1
        self.last_error = error
        self.last_error_time = datetime.now()
        self.status = ToolStatusENUM.ERROR
        
        # Also add to execution history
        self.add_to_execution_history({
            "error": error,
            "success": False,
            "timestamp": self.last_error_time.isoformat()
        })
    
    def is_ready(self) -> bool:
        """Check if tool is ready to execute"""
        return self.status == ToolStatusENUM.READY
    
    def is_available(self) -> bool:
        """Check if tool can be used (ready or uninitialized - will init on demand)"""
        return self.status in [ToolStatusENUM.READY, ToolStatusENUM.UNINITIALIZED]
    
    def get_recent_executions(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent n executions"""
        return self.execution_history[-n:] if self.execution_history else []
    
    def matches_query(self, query: str) -> float:
        """
        Calculate match score for a query (0.0 to 1.0).
        
        Args:
            query: The user query to match against
            
        Returns:
            Float score between 0 and 1 indicating match confidence
        """
        query_lower = query.lower()
        score = 0.0
        
        # Check keyword matches (highest weight)
        for keyword in self.keywords:
            if keyword.lower() in query_lower:
                score += 0.4
        
        # Check capability matches
        for capability in self.capabilities:
            if capability.lower() in query_lower:
                score += 0.3
        
        # Check name/description matches (lower weight)
        if self.name.lower() in query_lower:
            score += 0.2
        if any(word in query_lower for word in self.description.lower().split()):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "handler_name": self.handler_name,
            "llm_config": self.llm_config,
            "capabilities": self.capabilities,
            "keywords": self.keywords,
            "status": self.status.value,
            "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "execution_count": self.execution_count,
            "average_execution_time": self.average_execution_time,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"ToolEntryDTO(id='{self.tool_id}', "
            f"name='{self.name}', "
            f"status={self.status.value}, "
            f"executions={self.execution_count})"
        )