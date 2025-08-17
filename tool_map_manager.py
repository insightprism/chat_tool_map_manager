#!/usr/bin/env python3
"""
ToolMapManager - Core manager for the tool map

This module provides the ToolMapManager class which manages tool agents
in a session. It follows the same pattern as PersonaMapManager but is
simplified for tools which are stateless, one-shot executors.

Tools don't need conversation history or complex state management like personas.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import logging
import time

from .tool_entry_dto import ToolEntryDTO, ToolStatusENUM

logger = logging.getLogger(__name__)


class ToolMapManager:
    """
    Core manager for the tool map - parallel to PersonaMapManager.
    
    This class manages tools in a session, following the same pattern as
    PersonaMapManager but simplified for tools' specific needs:
    - No conversation history
    - No prompt tracking
    - Stateless execution
    - Lightweight initialization
    
    Key insights:
    - Every session can have a tool map for multi-agent tool coordination
    - Tools are one-shot executors, not conversational agents
    - Tool selection is based on capabilities and keywords
    - Execution history is limited and for debugging/stats only
    """
    
    def __init__(self, session_id: str, max_tools: int = 20):
        """
        Initialize the ToolMapManager.
        
        Args:
            session_id: Unique identifier for this session (same as PersonaMapManager)
            max_tools: Maximum number of tools allowed (default 20)
        """
        self.session_id = session_id
        self.max_tools = max_tools
        self._tool_map: Dict[str, ToolEntryDTO] = {}
        self._initialization_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics tracking
        self.total_added = 0
        self.total_removed = 0
        self.total_executions = 0
        self.created_at = datetime.now()
        
        logger.info(f"ToolMapManager created for session {session_id}")
    
    async def add_tool(
        self,
        tool_id: str,
        tool_instance: Any,
        name: str = "",
        description: str = "",
        handler_name: str = "",
        llm_config: Optional[Dict[str, Any]] = None,
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """
        Add a tool to the map.
        
        This is simpler than add_persona because tools don't need:
        - Conversation history
        - Demographics/behavioral traits
        - Hierarchy/reporting structure
        - Team assignments
        
        Args:
            tool_id: Unique identifier for this tool
            tool_instance: The tool instance implementing ToolInterface
            name: Display name of the tool
            description: Brief description
            handler_name: Handler for processing
            llm_config: LLM configuration dict
            system_prompt: System prompt for the tool
            capabilities: What this tool can do
            keywords: Keywords for matching
            metadata: Additional metadata
            **kwargs: Additional arguments for ToolEntryDTO
            
        Returns:
            bool: True if tool was added, False if already exists or at capacity
        """
        # Check capacity
        if len(self._tool_map) >= self.max_tools:
            logger.warning(f"Session at maximum tool capacity ({self.max_tools} tools)")
            return False
        
        # Check if already exists
        if tool_id in self._tool_map:
            logger.warning(f"Tool {tool_id} already exists in session {self.session_id}")
            return False
        
        # Create the ToolEntryDTO
        entry = ToolEntryDTO(
            tool_id=tool_id,
            tool_instance=tool_instance,
            name=name or tool_id,
            description=description or "",
            handler_name=handler_name or "",
            llm_config=llm_config or {},
            system_prompt=system_prompt or "",
            capabilities=capabilities or [],
            keywords=keywords or [],
            status=ToolStatusENUM.UNINITIALIZED,
            metadata=metadata or {}
        )
        
        # Add to map
        self._tool_map[tool_id] = entry
        self.total_added += 1
        
        # Initialize tool asynchronously if it has an initialize method
        if hasattr(tool_instance, 'initialize'):
            init_task = asyncio.create_task(
                self._initialize_tool(tool_id)
            )
            self._initialization_tasks[tool_id] = init_task
        else:
            # Mark as ready if no initialization needed
            entry.status = ToolStatusENUM.READY
            entry.initialized_at = datetime.now()
        
        logger.info(f"Added tool {tool_id} ({name}) to session {self.session_id}")
        return True
    
    async def remove_tool(self, tool_id: str) -> bool:
        """
        Remove a tool from the map.
        
        Args:
            tool_id: ID of tool to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if tool_id not in self._tool_map:
            logger.warning(f"Tool {tool_id} not found in session {self.session_id}")
            return False
        
        # Cancel initialization if still pending
        if tool_id in self._initialization_tasks:
            self._initialization_tasks[tool_id].cancel()
            del self._initialization_tasks[tool_id]
        
        # Remove from map
        del self._tool_map[tool_id]
        self.total_removed += 1
        
        logger.info(f"Removed tool {tool_id} from session {self.session_id}")
        return True
    
    def get_tool(self, tool_id: str) -> Optional[ToolEntryDTO]:
        """Get a specific tool by ID"""
        return self._tool_map.get(tool_id)
    
    def get_all_tools(self) -> Dict[str, ToolEntryDTO]:
        """Get all tools in the map"""
        return self._tool_map.copy()
    
    def get_ready_tools(self) -> Dict[str, ToolEntryDTO]:
        """Get only ready tools"""
        return {
            tid: entry for tid, entry in self._tool_map.items()
            if entry.status == ToolStatusENUM.READY
        }
    
    def get_tools_by_capability(self, capability: str) -> Dict[str, ToolEntryDTO]:
        """Get all tools with a specific capability"""
        return {
            tid: entry for tid, entry in self._tool_map.items()
            if capability in entry.capabilities
        }
    
    def get_tools_by_status(self, status: ToolStatusENUM) -> Dict[str, ToolEntryDTO]:
        """Get all tools with a specific status"""
        return {
            tid: entry for tid, entry in self._tool_map.items()
            if entry.status == status
        }
    
    def find_matching_tools(self, query: str, threshold: float = 0.3) -> List[Tuple[str, ToolEntryDTO, float]]:
        """
        Find tools that match the query.
        
        Args:
            query: The user query to match against
            threshold: Minimum confidence score (0-1)
            
        Returns:
            List of (tool_id, ToolEntryDTO, confidence_score) tuples,
            sorted by confidence (highest first)
        """
        matches = []
        
        for tool_id, entry in self._tool_map.items():
            # Skip unavailable tools
            if not entry.is_available():
                continue
            
            score = entry.matches_query(query)
            if score >= threshold:
                matches.append((tool_id, entry, score))
        
        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches
    
    async def execute_tool(
        self,
        tool_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with given context.
        
        Args:
            tool_id: ID of tool to execute
            context: Execution context (query, parameters, etc.)
            
        Returns:
            Execution result dictionary
        """
        entry = self._tool_map.get(tool_id)
        
        if not entry:
            return {
                "success": False,
                "error": f"Tool {tool_id} not found",
                "tool": tool_id
            }
        
        # Initialize if needed
        if entry.status == ToolStatusENUM.UNINITIALIZED:
            await self._ensure_tool_initialized(tool_id)
        
        if not entry.is_ready():
            return {
                "success": False,
                "error": f"Tool {tool_id} is not ready (status: {entry.status.value})",
                "tool": tool_id
            }
        
        # Mark as executing
        entry.status = ToolStatusENUM.EXECUTING
        start_time = time.time()
        
        try:
            # Execute the tool
            result = await entry.tool_instance.execute(context)
            
            # Update statistics
            execution_time = time.time() - start_time
            entry.update_execution_stats(execution_time)
            self.total_executions += 1
            
            # Add to execution history
            entry.add_to_execution_history({
                "query": context.get("query", ""),
                "result": str(result).replace('\n', ' ')[:200],  # Truncated for history
                "success": result.get("success", False),
                "execution_time": execution_time
            })
            
            # Mark as ready again
            entry.status = ToolStatusENUM.READY
            
            logger.info(f"Executed tool {tool_id} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            # Record error
            error_msg = str(e)
            entry.record_error(error_msg)
            logger.error(f"Error executing tool {tool_id}: {error_msg}", exc_info=True)
            
            # Try to recover status
            entry.status = ToolStatusENUM.READY
            
            return {
                "success": False,
                "error": error_msg,
                "tool": tool_id
            }
    
    async def execute_multiple_tools(
        self,
        tool_ids: List[str],
        context: Dict[str, Any],
        sequential: bool = True
    ) -> Dict[str, Any]:
        """
        Execute multiple tools.
        
        Args:
            tool_ids: List of tool IDs to execute
            context: Shared execution context
            sequential: If True, execute sequentially; if False, in parallel
            
        Returns:
            Dictionary with results from all tools
        """
        results = {
            "tools_executed": [],
            "tool_results": {},
            "success": True,
            "total_time": 0
        }
        
        start_time = time.time()
        
        if sequential:
            # Execute tools one by one
            for tool_id in tool_ids:
                result = await self.execute_tool(tool_id, context)
                results["tools_executed"].append(tool_id)
                results["tool_results"][tool_id] = result
                
                # Add previous results to context for next tool
                if result.get("success"):
                    context[f"{tool_id}_result"] = result
                else:
                    results["success"] = False
        else:
            # Execute tools in parallel
            tasks = [
                self.execute_tool(tool_id, context.copy())
                for tool_id in tool_ids
            ]
            
            tool_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for tool_id, result in zip(tool_ids, tool_results):
                if isinstance(result, Exception):
                    result = {
                        "success": False,
                        "error": str(result),
                        "tool": tool_id
                    }
                    results["success"] = False
                
                results["tools_executed"].append(tool_id)
                results["tool_results"][tool_id] = result
        
        results["total_time"] = time.time() - start_time
        return results
    
    async def wait_for_tool_initialization(self, tool_id: str, timeout: float = 10.0) -> bool:
        """
        Wait for a specific tool's initialization to complete.
        
        Args:
            tool_id: ID of tool to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if initialization completed, False if timeout
        """
        if tool_id not in self._initialization_tasks:
            # Check if already initialized
            entry = self._tool_map.get(tool_id)
            return entry and entry.status == ToolStatusENUM.READY
        
        try:
            await asyncio.wait_for(self._initialization_tasks[tool_id], timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for {tool_id} initialization")
            return False
        except Exception as e:
            logger.error(f"Error waiting for {tool_id} initialization: {e}")
            return False
    
    async def wait_for_all_initializations(self, timeout: float = 10.0) -> bool:
        """
        Wait for all pending tool initializations to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if all completed, False if any failed or timeout
        """
        if not self._initialization_tasks:
            return True
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._initialization_tasks.values()),
                timeout=timeout
            )
            self._initialization_tasks.clear()
            return True
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for tool initializations")
            return False
        except Exception as e:
            logger.error(f"Error waiting for tool initializations: {e}")
            return False
    
    async def _initialize_tool(self, tool_id: str):
        """
        Initialize a tool asynchronously.
        
        This runs in the background to set up the tool's LLM engine.
        """
        try:
            entry = self._tool_map[tool_id]
            
            # Call the tool's initialize method
            if hasattr(entry.tool_instance, 'initialize'):
                success = await entry.tool_instance.initialize()
                
                if success:
                    entry.status = ToolStatusENUM.READY
                    entry.initialized_at = datetime.now()
                    logger.info(f"Initialized tool {tool_id} successfully")
                else:
                    entry.status = ToolStatusENUM.ERROR
                    logger.error(f"Failed to initialize tool {tool_id}")
            else:
                # No initialization needed
                entry.status = ToolStatusENUM.READY
                entry.initialized_at = datetime.now()
                
        except Exception as e:
            logger.error(f"Failed to initialize tool {tool_id}: {e}")
            if tool_id in self._tool_map:
                self._tool_map[tool_id].status = ToolStatusENUM.ERROR
                self._tool_map[tool_id].record_error(str(e))
        
        finally:
            # Clean up the task reference
            if tool_id in self._initialization_tasks:
                del self._initialization_tasks[tool_id]
    
    async def _ensure_tool_initialized(self, tool_id: str):
        """Ensure a tool is initialized before use"""
        entry = self._tool_map.get(tool_id)
        if not entry:
            return
        
        if entry.status == ToolStatusENUM.UNINITIALIZED:
            await self._initialize_tool(tool_id)
    
    def count(self) -> int:
        """Get total number of tools"""
        return len(self._tool_map)
    
    def count_ready(self) -> int:
        """Get number of ready tools"""
        return len(self.get_ready_tools())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about this tool map"""
        ready_count = self.count_ready()
        total_count = self.count()
        
        # Calculate average execution time across all tools
        total_exec_time = sum(e.total_execution_time for e in self._tool_map.values())
        total_exec_count = sum(e.execution_count for e in self._tool_map.values())
        avg_exec_time = total_exec_time / total_exec_count if total_exec_count > 0 else 0
        
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "total_tools": total_count,
            "ready_tools": ready_count,
            "uninitialized_tools": len(self.get_tools_by_status(ToolStatusENUM.UNINITIALIZED)),
            "error_tools": len(self.get_tools_by_status(ToolStatusENUM.ERROR)),
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "total_executions": self.total_executions,
            "average_execution_time": avg_exec_time,
            "max_tools": self.max_tools,
            "capacity_used": (total_count / self.max_tools) * 100 if self.max_tools > 0 else 0
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools with basic info"""
        return [
            {
                "id": tool_id,
                "name": entry.name,
                "description": entry.description,
                "status": entry.status.value,
                "capabilities": entry.capabilities,
                "execution_count": entry.execution_count
            }
            for tool_id, entry in self._tool_map.items()
        ]
    
    async def cleanup(self):
        """Clean up all tools and resources"""
        # Cancel all pending initialization tasks
        for task in self._initialization_tasks.values():
            task.cancel()
        
        # Clean up all tools
        for tool_id in list(self._tool_map.keys()):
            await self.remove_tool(tool_id)
        
        logger.info(f"Cleaned up tool map for session {self.session_id}")
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"ToolMapManager(session='{self.session_id}', "
            f"tools={self.count()}, "
            f"ready={self.count_ready()}, "
            f"executions={self.total_executions})"
        )