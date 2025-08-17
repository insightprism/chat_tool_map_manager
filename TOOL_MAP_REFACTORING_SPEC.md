# Tool Map Manager Refactoring Specification

**Version:** 1.0  
**Date:** August 17, 2024  
**Status:** APPROVED FOR IMPLEMENTATION  
**Author:** Claude Code Assistant  

## Executive Summary

This specification defines the refactoring of ToolMapManager from DIYyid application into a standalone, reusable package. The refactoring extracts generic tool management capabilities into an independent infrastructure package that any application can use, while maintaining all existing DIYyid functionality through an adapter pattern.

## 1. Purpose and Motivation

### 1.1 Current State Problems

Currently, ToolMapManager is tightly coupled to the DIYyid application through:

1. **Hardcoded application paths** - Default directory assumes DIYyid structure
2. **Direct JsonToolAgent dependency** - Imports DIYyid-specific tool implementation
3. **Mixed responsibilities** - Generic tool management mixed with DIYyid-specific loading logic
4. **Limited reusability** - Other applications cannot use ToolMapManager without DIYyid dependencies

### 1.2 Why This Refactoring is Needed

The user correctly identified that ToolMapManager, like PersonaMapManager, is a powerful abstraction that other applications using PM Chat App v2 would want to use. Currently:

- ToolMapManager provides excellent session-level tool management
- It follows proven patterns from PersonaMapManager
- It solves thread-safety issues with singleton tools
- But it's locked inside DIYyid application

### 1.3 Benefits of Refactoring

1. **True Reusability**: Any application can use tool management without DIYyid
2. **Clean Architecture**: Clear separation between infrastructure and application
3. **Independent Evolution**: Package can be versioned and updated independently
4. **Better Testing**: Generic components can be tested in isolation
5. **Reduced Coupling**: DIYyid becomes a consumer of the package, not the owner
6. **Community Contribution**: Package can be shared/open-sourced if desired

## 2. Architecture Design

### 2.1 Package Structure

```
/home/markly2/claude_code/tool_map_infrastructure/  # NEW standalone package
├── __init__.py                    # Package initialization and exports
├── tool_entry_dto.py              # Data structure for tool entries
├── tool_map_manager.py            # Core tool management (generic)
├── tool_interface.py              # Protocol/interface for tools
└── README.md                      # Package documentation

/home/markly2/claude_code/diyyid_app/              # DIYyid changes
├── tool_agents/
│   ├── diy_tool_loader.py        # NEW: DIYyid-specific loading logic
│   ├── tool_registry.py          # UNCHANGED: Keeps JsonToolAgent
│   └── smart_tool_selector.py    # MODIFIED: Import updates
└── backend_server.py              # MODIFIED: Uses package + loader
```

### 2.2 Separation of Concerns

**Generic (tool_map_infrastructure package):**
- Tool entry data structure (DTO)
- Tool lifecycle management (add, remove, get)
- Tool execution orchestration
- Tool discovery by capability/keywords
- Statistics and monitoring
- Async initialization handling

**Application-Specific (DIYyid):**
- JSON file loading from directories
- JsonToolAgent creation
- DIYyid-specific tool patterns
- Integration with DIYyid's persona system

## 3. Implementation Details

### 3.1 Files to Create

#### 3.1.1 `/home/markly2/claude_code/tool_map_infrastructure/__init__.py`
```python
"""
Tool Map Infrastructure - Reusable tool management for multi-agent systems

This package provides generic tool management capabilities that can be used
by any application needing to manage stateless tool agents in sessions.
"""

from .tool_entry_dto import ToolEntryDTO, ToolStatusENUM
from .tool_map_manager import ToolMapManager
from .tool_interface import ToolInterface

__version__ = "1.0.0"
__all__ = [
    "ToolMapManager",
    "ToolEntryDTO", 
    "ToolStatusENUM",
    "ToolInterface"
]
```

#### 3.1.2 `/home/markly2/claude_code/tool_map_infrastructure/tool_interface.py`
```python
"""Protocol/Interface for tool implementations"""

from typing import Protocol, Dict, Any, List, Optional
from abc import ABC, abstractmethod

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
```

#### 3.1.3 `/home/markly2/claude_code/diyyid_app/tool_agents/diy_tool_loader.py`
```python
"""DIYyid-specific tool loading logic"""

import json
import logging
from pathlib import Path
from typing import Optional

from tool_map_infrastructure import ToolMapManager
from .tool_registry import JsonToolAgent

logger = logging.getLogger(__name__)

class DIYToolLoader:
    """Loads DIYyid-specific JsonToolAgent tools into ToolMapManager"""
    
    def __init__(self, tool_manager: ToolMapManager):
        self.tool_manager = tool_manager
    
    async def load_tools_from_directory(self, directory: Path = None) -> int:
        """
        Load all tool JSON files from a directory.
        
        This method was moved from ToolMapManager to keep
        DIYyid-specific logic separate from generic infrastructure.
        
        Args:
            directory: Directory containing *_tool.json files
                      Defaults to DIYyid's "personas" directory
            
        Returns:
            Number of tools loaded
        """
        if directory is None:
            # DIYyid-specific default path
            directory = Path(__file__).parent.parent / "personas"
        
        loaded_count = 0
        
        for tool_file in directory.glob("*_tool.json"):
            try:
                with open(tool_file) as f:
                    tool_config = json.load(f)
                
                # Create DIYyid-specific JsonToolAgent
                tool = JsonToolAgent(tool_config)
                
                # Add to generic tool manager
                success = await self.tool_manager.add_tool(
                    tool_id=tool.tool_id,
                    tool_instance=tool,
                    name=tool.name,
                    description=tool.description,
                    handler_name=tool_config.get("llm_handler_name", ""),
                    llm_config=tool_config.get("llm_config_persona", {}),
                    system_prompt=tool_config.get("system_prompt", ""),
                    capabilities=tool.capabilities,
                    keywords=tool.keywords
                )
                
                if success:
                    loaded_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to load tool from {tool_file}: {e}")
        
        logger.info(f"Loaded {loaded_count} tools into session {self.tool_manager.session_id}")
        return loaded_count
```

### 3.2 Files to Move (from DIYyid to package)

#### 3.2.1 `tool_entry_dto.py`
- Move AS-IS from `/home/markly2/claude_code/diyyid_app/tool_agents/tool_entry_dto.py`
- To: `/home/markly2/claude_code/tool_map_infrastructure/tool_entry_dto.py`
- No changes needed to the file content

#### 3.2.2 `tool_map_manager.py`
- Move from `/home/markly2/claude_code/diyyid_app/tool_agents/tool_map_manager.py`
- To: `/home/markly2/claude_code/tool_map_infrastructure/tool_map_manager.py`
- **REMOVE** the `load_tools_from_directory` method (lines 146-193)
- **REMOVE** the import `from .tool_registry import JsonToolAgent` (line 168)
- Update imports at top to be absolute

### 3.3 Files to Modify in DIYyid

#### 3.3.1 `/home/markly2/claude_code/diyyid_app/backend_server.py`

**Current code (lines ~252-270):**
```python
async def _add_tool_agents(self, session: Session):
    """Add tool agents using ToolMapManager - Refactored approach"""
    try:
        from tool_agents.tool_map_manager import ToolMapManager
        
        session.tool_manager = ToolMapManager(session.session_id)
        tools_loaded = await session.tool_manager.load_tools_from_directory()
        
        initialization_success = await session.tool_manager.wait_for_all_initializations(timeout=5.0)
        # ... rest of method
```

**Change to:**
```python
async def _add_tool_agents(self, session: Session):
    """Add tool agents using ToolMapManager - Refactored approach"""
    try:
        # Import from standalone package
        import sys
        sys.path.append('/home/markly2/claude_code/tool_map_infrastructure')
        from tool_map_infrastructure import ToolMapManager
        
        # Import DIYyid-specific loader
        from tool_agents.diy_tool_loader import DIYToolLoader
        
        # Create tool manager (generic)
        session.tool_manager = ToolMapManager(session.session_id)
        
        # Load tools using DIYyid-specific loader
        loader = DIYToolLoader(session.tool_manager)
        tools_loaded = await loader.load_tools_from_directory()
        
        # Wait for initialization (generic functionality)
        initialization_success = await session.tool_manager.wait_for_all_initializations(timeout=5.0)
        # ... rest of method unchanged
```

#### 3.3.2 `/home/markly2/claude_code/diyyid_app/tool_agents/smart_tool_selector.py`

**Current imports (line ~40):**
```python
from tool_agents.tool_map_manager import ToolMapManager
```

**Change to:**
```python
import sys
sys.path.append('/home/markly2/claude_code/tool_map_infrastructure')
from tool_map_infrastructure import ToolMapManager
```

#### 3.3.3 Test files that need import updates:
- `/home/markly2/claude_code/diyyid_app/test_tool_map_integration.py`
- `/home/markly2/claude_code/diyyid_app/phase2/test_tool_map_refactor.py`

Update imports from:
```python
from tool_agents.tool_map_manager import ToolMapManager
from tool_agents.tool_entry_dto import ToolEntryDTO, ToolStatusENUM
```

To:
```python
import sys
sys.path.append('/home/markly2/claude_code/tool_map_infrastructure')
from tool_map_infrastructure import ToolMapManager, ToolEntryDTO, ToolStatusENUM
from tool_agents.diy_tool_loader import DIYToolLoader
```

## 4. Functionality to Preserve

### 4.1 Critical Functions That Must Continue Working

1. **Tool Loading**: All 5 DIYyid tool JSON files must load correctly
   - image_analyzer_tool.json
   - cost_estimator_tool.json
   - safety_checker_tool.json
   - material_identifier_tool.json
   - web_search_tool.json

2. **Tool Discovery**: Finding tools by capability and keywords
3. **Tool Execution**: Tools must execute with same inputs/outputs
4. **Session Integration**: Tools work within PM Chat App v2 sessions
5. **Dynamic Attribute**: `session.tool_manager` pattern must work
6. **Async Initialization**: Tools initialize in background
7. **Statistics Tracking**: Execution counts and timing
8. **Error Handling**: Graceful failure and recovery

### 4.2 API Contracts to Maintain

1. **Tool execution returns:**
   ```python
   {"success": bool, "tool": str, "result": str, ...}
   ```

2. **SmartToolSelector.execute_tools() returns:**
   ```python
   {"tools_used": [], "tool_results": {}, "success": bool}
   ```

3. **Backend process_message() includes:**
   ```python
   {"response": str, "tools_used": [], "tool_results": {}}
   ```

## 5. Migration Steps

### 5.1 Step-by-Step Implementation

1. **Create package directory structure**
   ```bash
   mkdir -p /home/markly2/claude_code/tool_map_infrastructure
   ```

2. **Create new files in package**
   - Create `__init__.py`
   - Create `tool_interface.py`

3. **Move files to package**
   - Move `tool_entry_dto.py`
   - Move and modify `tool_map_manager.py`

4. **Create DIYyid adapter**
   - Create `diy_tool_loader.py`

5. **Update imports in DIYyid**
   - Update `backend_server.py`
   - Update `smart_tool_selector.py`
   - Update test files

6. **Test everything**
   - Run integration tests
   - Test WebSocket chat
   - Verify all tools load

## 6. Test Plan

### 6.1 Comprehensive Test Script

Create `/home/markly2/claude_code/diyyid_app/test_refactoring_validation.py`:

```python
#!/usr/bin/env python3
"""
Validation test for Tool Map Manager refactoring
Ensures all functionality is preserved after refactoring
"""

import sys
import asyncio
import json
from pathlib import Path

# Add paths
sys.path.append('/home/markly2/prismmind')
sys.path.append('/home/markly2/claude_code/pm_chat_app_backendonly_v2')
sys.path.append('/home/markly2/claude_code/tool_map_infrastructure')
sys.path.append('/home/markly2/claude_code/diyyid_app')

async def test_package_imports():
    """Test 1: Verify package can be imported"""
    print("\n=== Test 1: Package Imports ===")
    try:
        from tool_map_infrastructure import ToolMapManager, ToolEntryDTO, ToolStatusENUM
        print("✅ Package imports successful")
        return True
    except ImportError as e:
        print(f"❌ Package import failed: {e}")
        return False

async def test_tool_loading():
    """Test 2: Verify all 5 tools load correctly"""
    print("\n=== Test 2: Tool Loading ===")
    
    from tool_map_infrastructure import ToolMapManager
    from tool_agents.diy_tool_loader import DIYToolLoader
    
    # Create manager and loader
    manager = ToolMapManager("test_session")
    loader = DIYToolLoader(manager)
    
    # Load tools
    count = await loader.load_tools_from_directory()
    
    # Verify count
    if count >= 5:
        print(f"✅ Loaded {count} tools successfully")
    else:
        print(f"❌ Only loaded {count} tools, expected at least 5")
        return False
    
    # Verify specific tools
    expected_tools = [
        "image_analyzer_tool",
        "cost_estimator_tool",
        "safety_checker_tool",
        "material_identifier_tool",
        "web_search_tool"
    ]
    
    for tool_id in expected_tools:
        if manager.get_tool(tool_id):
            print(f"  ✅ {tool_id} loaded")
        else:
            print(f"  ❌ {tool_id} NOT found")
            return False
    
    return True

async def test_tool_execution():
    """Test 3: Verify tool execution works"""
    print("\n=== Test 3: Tool Execution ===")
    
    from tool_map_infrastructure import ToolMapManager
    from tool_agents.diy_tool_loader import DIYToolLoader
    
    # Setup
    manager = ToolMapManager("test_session")
    loader = DIYToolLoader(manager)
    await loader.load_tools_from_directory()
    
    # Wait for initialization
    await manager.wait_for_all_initializations(timeout=5.0)
    
    # Test cost estimator
    result = await manager.execute_tool(
        "cost_estimator_tool",
        {"query": "Fix a leaking pipe"}
    )
    
    if result.get("success"):
        print("✅ Tool execution successful")
        print(f"  Result preview: {str(result.get('estimate', ''))[:100]}...")
        return True
    else:
        print(f"❌ Tool execution failed: {result.get('error')}")
        return False

async def test_session_integration():
    """Test 4: Verify Session integration works"""
    print("\n=== Test 4: Session Integration ===")
    
    from pc_components.multi_agent.multi_persona_session_manager import Session
    from tool_map_infrastructure import ToolMapManager
    from tool_agents.diy_tool_loader import DIYToolLoader
    
    # Create session
    session = Session("test_session", max_personas=10)
    
    # Add tool manager dynamically
    session.tool_manager = ToolMapManager(session.session_id)
    
    # Verify attribute added
    if hasattr(session, 'tool_manager'):
        print("✅ Dynamic attribute addition works")
    else:
        print("❌ Failed to add tool_manager to session")
        return False
    
    # Load tools
    loader = DIYToolLoader(session.tool_manager)
    count = await loader.load_tools_from_directory()
    
    if count > 0:
        print(f"✅ Session integration successful with {count} tools")
        return True
    else:
        print("❌ Failed to load tools in session")
        return False

async def test_smart_selector():
    """Test 5: Verify SmartToolSelector works with refactored code"""
    print("\n=== Test 5: SmartToolSelector Integration ===")
    
    from tool_map_infrastructure import ToolMapManager
    from tool_agents.diy_tool_loader import DIYToolLoader
    from tool_agents.smart_tool_selector import SmartToolSelector
    
    # Setup
    manager = ToolMapManager("test_session")
    loader = DIYToolLoader(manager)
    await loader.load_tools_from_directory()
    await manager.wait_for_all_initializations(timeout=5.0)
    
    # Create selector
    selector = SmartToolSelector(manager)
    await selector.initialize()
    
    # Test tool selection
    selected = await selector.select_tools(
        "How much would it cost to fix a leak?",
        {}
    )
    
    if "cost_estimator_tool" in selected:
        print("✅ SmartToolSelector works correctly")
        print(f"  Selected tools: {selected}")
        return True
    else:
        print(f"❌ SmartToolSelector failed to select expected tool")
        print(f"  Selected: {selected}")
        return False

async def test_backward_compatibility():
    """Test 6: Verify existing code still works"""
    print("\n=== Test 6: Backward Compatibility ===")
    
    # Test that tool_registry still works independently
    from tool_agents.tool_registry import get_tool_registry
    
    registry = await get_tool_registry()
    
    if len(registry.tools) > 0:
        print(f"✅ Tool registry still works with {len(registry.tools)} tools")
        return True
    else:
        print("❌ Tool registry broken")
        return False

async def main():
    """Run all validation tests"""
    print("="*60)
    print("TOOL MAP MANAGER REFACTORING VALIDATION")
    print("="*60)
    
    tests = [
        test_package_imports,
        test_tool_loading,
        test_tool_execution,
        test_session_integration,
        test_smart_selector,
        test_backward_compatibility
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nRefactoring is SAFE to deploy!")
    else:
        print(f"⚠️ SOME TESTS FAILED ({passed}/{total} passed)")
        print("\nDO NOT deploy until all tests pass!")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

### 6.2 Manual Testing Checklist

After running automated tests, manually verify:

1. [ ] Start DIYyid application
2. [ ] Open web interface
3. [ ] Select a specialist (plumber/electrician/handyman)
4. [ ] Send a message that triggers tool usage
5. [ ] Upload an image and verify image analyzer works
6. [ ] Verify cost estimation tool responds
7. [ ] Check browser console for errors
8. [ ] Review application logs for warnings

## 7. Risk Mitigation

### 7.1 Rollback Plan

If issues are discovered:

1. **Quick Rollback**: 
   - Move files back to original location
   - Revert import changes
   - Total time: ~5 minutes

2. **Gradual Rollback**:
   - Keep package but add compatibility layer
   - Gradually migrate back if needed

### 7.2 Potential Issues and Solutions

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import errors | Low | High | Test imports first |
| Tools don't load | Low | High | Validate with test script |
| Performance degradation | Very Low | Medium | Benchmark before/after |
| Session integration breaks | Low | High | Test with Session object |

## 8. Success Criteria

The refactoring is successful when:

1. ✅ All 6 validation tests pass
2. ✅ Manual testing shows no regression
3. ✅ Code is cleaner and more modular
4. ✅ Package can be imported independently
5. ✅ DIYyid functionality unchanged
6. ✅ Documentation is updated

## 9. Implementation Notes for Claude Code

### Context You Need to Understand

1. **The Magic One-Liner Still Works**: 
   ```python
   session.tool_manager = ToolMapManager(session.session_id)
   ```
   This dynamic attribute pattern is preserved

2. **JsonToolAgent Stays in DIYyid**:
   - It's DIYyid's specific implementation
   - Other apps would have their own tool implementations

3. **Pattern Matching is Generic**:
   - `*_tool.json` pattern is good for any app
   - Keep this in ToolMapManager, not DIYyid-specific

4. **Test Thoroughly**:
   - Run the validation script after each major step
   - Don't proceed if tests fail

5. **Path Management**:
   - Use sys.path.append for now
   - Could make proper package with setup.py later

## 10. Future Enhancements

After successful refactoring:

1. **Package Distribution**:
   - Add setup.py for pip installation
   - Publish to private PyPI if desired

2. **Additional Features**:
   - Tool versioning
   - Tool dependencies
   - Tool composition/chaining

3. **Documentation**:
   - API documentation
   - Usage examples
   - Integration guides

## Appendix A: File Mappings

| Current Location | New Location | Action |
|-----------------|--------------|--------|
| diyyid_app/tool_agents/tool_entry_dto.py | tool_map_infrastructure/tool_entry_dto.py | Move |
| diyyid_app/tool_agents/tool_map_manager.py | tool_map_infrastructure/tool_map_manager.py | Move & Modify |
| N/A | tool_map_infrastructure/__init__.py | Create |
| N/A | tool_map_infrastructure/tool_interface.py | Create |
| N/A | diyyid_app/tool_agents/diy_tool_loader.py | Create |

## Appendix B: Import Changes

| File | Old Import | New Import |
|------|------------|------------|
| backend_server.py | `from tool_agents.tool_map_manager import ToolMapManager` | `from tool_map_infrastructure import ToolMapManager` |
| smart_tool_selector.py | `from tool_agents.tool_map_manager import ToolMapManager` | `from tool_map_infrastructure import ToolMapManager` |
| Test files | `from tool_agents.tool_entry_dto import ToolEntryDTO` | `from tool_map_infrastructure import ToolEntryDTO` |

---

**END OF SPECIFICATION**

This specification provides complete guidance for refactoring ToolMapManager into a reusable package while maintaining all DIYyid functionality.