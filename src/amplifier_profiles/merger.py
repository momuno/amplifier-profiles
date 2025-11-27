"""Profile merging utilities for inheritance.

This module implements deep merging of profile configurations, allowing child
profiles to be partial and inherit from parent profiles without duplication.

Key principles:
- Module lists (hooks/tools/providers) are merged by module ID
- Config dictionaries are recursively deep-merged
- Sources are inherited - child profiles don't need to repeat git URLs
- Scalars override - simple values in child replace parent values

This supports the "merge-then-validate" pattern where validation happens
after the complete inheritance chain is merged.
"""
import logging

from typing import Any

logger = logging.getLogger(__name__)

def merge_profile_dicts(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge child profile dictionary into parent profile dictionary.

    Merge rules by key:
    - 'hooks', 'tools', 'providers', 'agents': Merge module lists by ID/name
    - Dict values: Recursive deep merge
    - Other values: Child overrides parent

    Args:
        parent: Parent profile dictionary (loaded from parent profile)
        child: Child profile dictionary (loaded from child profile)

    Returns:
        Merged profile dictionary with child values taking precedence

    Example:
        >>> parent = {
        ...     "hooks": [{"module": "hooks-A", "source": "git+...", "config": {"a": 1}}],
        ...     "session": {"orchestrator": {"module": "X", "source": "git+..."}},
        ... }
        >>> child = {
        ...     "hooks": [{"module": "hooks-A", "config": {"b": 2}}],
        ...     "session": {"context": {"module": "Y"}},
        ... }
        >>> result = merge_profile_dicts(parent, child)
        >>> result["hooks"][0]["source"]  # Inherited from parent
        'git+...'
        >>> result["hooks"][0]["config"]  # Merged
        {'a': 1, 'b': 2}
        >>> result["session"]["orchestrator"]["module"]  # Inherited
        'X'
        >>> result["session"]["context"]["module"]  # Added
        'Y'
    """
    merged = parent.copy()

    for key, child_value in child.items():
        if key not in merged:
            # New key in child - just add it
            merged[key] = child_value
        elif key in ("hooks", "tools", "providers", "agents"):
            # Module lists - merge by module ID (tools/providers/hooks) or name (agents)
            # Special case: agents.include is a filter operation, not a merge
            if key == "agents" and isinstance(child_value, dict) and "include" in child_value:
                # Child specifies agents.include: [...] - this is FILTER intent
                include_list = child_value.get("include")
                if isinstance(include_list, list) and include_list and isinstance(merged[key], list):
                    # Filter parent agents list to only included names
                    filtered_agents = [
                        agent for agent in merged[key]
                        if agent.get("name") in include_list
                    ]
                    merged[key] = filtered_agents
                    logger.debug(f"Filtered agents to: {[a.get('name') for a in filtered_agents]}")
                else:
                    # Empty or invalid include list, inherit all
                    # merged[key] stays as parent's value
                    pass
            else:
                # Normal module list merge by ID/name
                merged[key] = merge_module_lists(merged[key], child_value)
        elif key == "agents":
            # DEPRECATED PATH: agents as dict (backward compatibility)
            # This branch handles old dict structure during transition
            if isinstance(merged[key], dict) and isinstance(child_value, dict):
                # Both are dicts - log deprecation warning
                logger.warning(
                    "DEPRECATED: agents as dict is deprecated. "
                    "Please migrate to list structure. "
                    "See migration guide: docs/MIGRATION_AGENTS_TO_LIST.md"
                )
                # Deep merge for backward compatibility
                merged[key] = merge_dicts(merged[key], child_value)
            else:
                # Type mismatch - child overrides (forces migration)
                merged[key] = child_value
            merged[key] = merge_module_lists(merged[key], child_value)
        elif isinstance(child_value, dict) and isinstance(merged[key], dict):
            # Both are dicts - recursive deep merge
            merged[key] = merge_dicts(merged[key], child_value)
        else:
            # Scalar or type mismatch - child overrides parent
            merged[key] = child_value

    return merged


def merge_module_lists(parent_list: list[dict[str, Any]], child_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Merge module lists by module ID, deep-merging configs.

    Module lists (hooks, tools, providers, agents) are matched by 'module' or 'name' field.
    When the same module appears in both lists, their configs are deep-merged.

    Args:
        parent_list: Parent module list
        child_list: Child module list

    Returns:
        Merged module list with deep-merged configs

    Example:
        >>> parent = [{"module": "A", "source": "git+...", "config": {"x": 1}}]
        >>> child = [{"module": "A", "config": {"y": 2}}]
        >>> result = merge_module_lists(parent, child)
        >>> result[0]["source"]  # Inherited
        'git+...'
        >>> result[0]["config"]  # Merged
        {'x': 1, 'y': 2}
    """
    # Build dict indexed by module ID for efficient lookup
    result: dict[str, dict[str, Any]] = {}

    # Determine ID field: "module" for tools/providers/hooks, "name" for agents
    id_field = "module"
    if parent_list and "name" in parent_list[0]:
        id_field = "name"
    elif child_list and "name" in child_list[0]:
        id_field = "name"

    # Add all parent modules
    for item in parent_list:
        module_id = item.get(id_field)
        if module_id:
            result[module_id] = item.copy()

    # Merge or add child modules
    for child_item in child_list:
        module_id = child_item.get(id_field)
        if not module_id:
            # No module ID - can't merge, just append
            continue

        if module_id in result:
            # Same module in parent - deep merge
            result[module_id] = merge_module_items(result[module_id], child_item)
        else:
            # New module in child - add it
            result[module_id] = child_item.copy()

    # Return as list (order preserved from parent, then new child modules)
    return list(result.values())


def merge_module_items(parent_item: dict[str, Any], child_item: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge a single module item (hook/tool/provider config).

    Special handling for 'config' field - deep merged rather than replaced.
    All other fields follow standard merge rules (child overrides parent).

    Args:
        parent_item: Parent module item
        child_item: Child module item

    Returns:
        Merged module item

    Example:
        >>> parent = {"module": "A", "source": "git+...", "config": {"x": 1}}
        >>> child = {"module": "A", "config": {"y": 2}}
        >>> result = merge_module_items(parent, child)
        >>> result
        {'module': 'A', 'source': 'git+...', 'config': {'x': 1, 'y': 2}}
    """
    merged = parent_item.copy()

    for key, value in child_item.items():
        if key == "config" and key in merged:
            # Deep merge configs
            if isinstance(merged["config"], dict) and isinstance(value, dict):
                merged["config"] = merge_dicts(merged["config"], value)
            else:
                # Type mismatch or not dicts - child overrides
                merged["config"] = value
        else:
            # All other fields: child overrides parent (including 'source')
            merged[key] = value

    return merged


def merge_dicts(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """
    Recursive deep merge of two dictionaries.

    Child values override parent values at all nesting levels.
    If both parent and child have dict values for same key, merge recursively.

    Args:
        parent: Parent dictionary
        child: Child dictionary

    Returns:
        Merged dictionary

    Example:
        >>> parent = {"a": 1, "b": {"x": 1, "y": 2}}
        >>> child = {"b": {"x": 10, "z": 3}, "c": 4}
        >>> result = merge_dicts(parent, child)
        >>> result
        {'a': 1, 'b': {'x': 10, 'y': 2, 'z': 3}, 'c': 4}
    """
    merged = parent.copy()

    for key, value in child.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Both are dicts - recurse
            merged[key] = merge_dicts(merged[key], value)
        else:
            # Scalar, list, or type mismatch - child overrides
            merged[key] = value

    return merged
