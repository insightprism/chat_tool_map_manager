# Tool Map Infrastructure

**Version:** 1.0.0  
**Date:** August 17, 2024  
**Status:** Production Ready

## Overview

This directory contains the **Tool Map Infrastructure** - a standalone, reusable package for managing stateless tool agents in multi-agent systems. It was refactored from the DIYyid application to provide generic tool management capabilities that any application can use.

## Structure

```
chat_tool_map_manager/
├── README.md                          # This file
├── TOOL_MAP_REFACTORING_SPEC.md      # Detailed refactoring specification
└── tool_map_infrastructure/           # Standalone package
    ├── __init__.py                    # Package exports
    ├── tool_entry_dto.py              # Data structure for tools
    ├── tool_map_manager.py            # Core tool management
    └── tool_interface.py              # Protocol for tool implementations
```

## Key Features

- **Session-level tool management** - Each session has its own tool manager
- **Thread-safe** - No shared mutable state between sessions
- **Async initialization** - Tools initialize in background
- **Dynamic discovery** - Find tools by capability or keywords
- **Execution tracking** - Statistics and history for debugging
- **Clean separation** - Generic infrastructure vs application-specific logic

## Usage

### Basic Usage

```python
import sys
sys.path.append('/home/markly2/claude_code/chat_tool_map_manager')
from tool_map_infrastructure import ToolMapManager

# Create a tool manager for a session
tool_manager = ToolMapManager("session_123")

# Add a tool
await tool_manager.add_tool(
    tool_id="my_tool",
    tool_instance=my_tool_implementation,
    name="My Tool",
    description="Does something useful",
    capabilities=["capability1"],
    keywords=["keyword1", "keyword2"]
)

# Execute a tool
result = await tool_manager.execute_tool("my_tool", {"query": "test"})
```

### Integration with PM Chat App v2 Sessions

```python
from pc_components.multi_agent.multi_persona_session_manager import Session
from tool_map_infrastructure import ToolMapManager

# Create session
session = Session("session_id", max_personas=10)

# Dynamically add tool manager
session.tool_manager = ToolMapManager(session.session_id)

# Now session has tool management capabilities!
```

### Application-Specific Loading (DIYyid Example)

```python
from tool_map_infrastructure import ToolMapManager
from tool_agents.diy_tool_loader import DIYToolLoader

# Create manager
tool_manager = ToolMapManager("session_id")

# Use application-specific loader
loader = DIYToolLoader(tool_manager)
tools_loaded = await loader.load_tools_from_directory()
```

## Tool Interface

Tools must implement the following protocol:

```python
class ToolInterface(Protocol):
    tool_id: str
    name: str
    description: str
    capabilities: List[str]
    keywords: List[str]
    
    async def initialize(self) -> bool:
        """Initialize tool resources"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool"""
    
    def matches_query(self, query: str) -> float:
        """Return confidence score (0-1)"""
```

## Benefits

1. **Reusability** - Any application can use this package
2. **Clean Architecture** - Separation of concerns
3. **Type Safety** - Proper DTOs and protocols
4. **Performance** - No unnecessary conversation history
5. **Maintainability** - Clear, documented interfaces

## Testing

Run validation tests:

```bash
cd /home/markly2/claude_code/diyyid_app
python3 test_refactoring_validation.py
```

Expected output:
```
✅ ALL TESTS PASSED (6/6)
Refactoring is SAFE to deploy!
```

## Migration from DIYyid

If you're migrating from the old DIYyid-embedded version:

1. Update imports:
   ```python
   # Old
   from tool_agents.tool_map_manager import ToolMapManager
   
   # New
   import sys
   sys.path.append('/home/markly2/claude_code/chat_tool_map_manager')
   from tool_map_infrastructure import ToolMapManager
   ```

2. Use loader for DIYyid-specific logic:
   ```python
   # Old
   await tool_manager.load_tools_from_directory()
   
   # New
   from tool_agents.diy_tool_loader import DIYToolLoader
   loader = DIYToolLoader(tool_manager)
   await loader.load_tools_from_directory()
   ```

## Future Enhancements

- Package as proper Python package with setup.py
- Add tool versioning support
- Tool dependency management
- Tool composition/chaining
- Publish to PyPI for easier distribution

## License

This package is part of the PM Chat App v2 ecosystem and follows its licensing terms.

## Support

For issues or questions, refer to the specification document:
`TOOL_MAP_REFACTORING_SPEC.md`