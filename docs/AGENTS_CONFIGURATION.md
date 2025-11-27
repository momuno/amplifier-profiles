# Agents Configuration Guide

This guide explains how to configure agents in Amplifier profiles with full control over inheritance and filtering.

## Structure

```yaml
agents:
  items:  # Explicit agent definitions (OPTIONAL)
    - name: agent-name
      source: git+https://...  # Optional, can inherit from parent
      config: {}  # Optional agent-specific config
  dirs:  # Directories to discover agents (OPTIONAL)
    - ./agents
    - ./custom-agents
  include-only:  # Filter: only these agents are active (OPTIONAL)
    - agent-name-1
    - agent-name-2
```

**Note:** All three fields (`items`, `dirs`, `include-only`) are optional. You can:
- Use only `dirs` for auto-discovery
- Use only `items` for explicit definitions
- Use both `items` and `dirs` for mixed approach
- Add `include-only` to filter any combination

## Inheritance Behavior

### 1. No agents key (full inheritance)
```yaml
profile:
  extends: parent
# No agents key - inherits everything from parent
```
**Result:** Child gets all parent's agents, dirs, and include-only settings.

### 2. Explicit reset with empty list
```yaml
profile:
  extends: parent
agents: []
```
**Result:** Child has NO agents, NO dirs (complete reset).

### 3. Add new agents to parent's list
```yaml
# Parent profile
agents:
  items:
    - name: zen-architect
      source: git+https://example.com/zen-architect
    - name: bug-hunter
      source: git+https://example.com/bug-hunter

# Child profile
agents:
  items:
    - name: beads-expert
      source: git+https://example.com/beads-expert
```
**Result:** Child has zen-architect, bug-hunter, AND beads-expert (all 3).

### 4. Override agent source
```yaml
# Parent profile
agents:
  items:
    - name: zen-architect
      source: git+https://example.com/zen-architect@v1

# Child profile
agents:
  items:
    - name: zen-architect
      source: git+https://example.com/zen-architect@v2  # Override version
```
**Result:** Child has zen-architect with v2 source.

### 5. Filter with include-only
```yaml
# Parent profile
agents:
  items:
    - name: zen-architect
    - name: bug-hunter
    - name: test-coverage
    - name: refactor-architect

# Child profile
agents:
  include-only:
    - zen-architect
    - bug-hunter
```
**Result:** Child has ONLY zen-architect and bug-hunter (others filtered out).

### 6. Add new agent AND filter
```yaml
# Parent profile
agents:
  items:
    - name: zen-architect
      source: git+arch
    - name: bug-hunter
      source: git+bug
    - name: test-coverage
      source: git+test

# Child profile
agents:
  items:
    - name: beads-expert
      source: git+beads
  include-only:
    - zen-architect
    - beads-expert
```
**Result:** Child has zen-architect and beads-expert (bug-hunter and test-coverage filtered out).

### 7. Directory discovery
```yaml
# Parent profile
agents:
  dirs:
    - ./agents

# Child profile
agents:
  dirs:
    - ./custom-agents
```
**Result:** Child discovers agents from BOTH ./agents and ./custom-agents (dirs append).

### 8. Directory discovery with filtering
```yaml
# Parent profile
agents:
  dirs:
    - ./agents  # Contains: zen-architect, bug-hunter, test-coverage

# Child profile
agents:
  dirs:
    - ./custom-agents  # Contains: beads-expert
  include-only:
    - zen-architect
    - beads-expert
```
**Result:** Child discovers from both directories but only keeps zen-architect and beads-expert.

## Complete Examples

### Example 1: Discovery-Only Profile (Auto-discover all agents)
```yaml
# profiles/base.yaml
profile:
  name: base
  version: 1.0.0
  description: Base profile that discovers agents from directory

session:
  orchestrator:
    module: loop-streaming
    source: git+https://...
  context:
    module: context-enhanced
    source: git+https://...

agents:
  dirs:
    - ./agents  # Discovers all .md files in this directory
    # No items needed - agents are auto-discovered
```
**Result:** All agents found in ./agents directory are loaded.

### Example 2: Discovery with Filtering
```yaml
# profiles/dev.yaml
profile:
  name: dev
  version: 1.0.0
  description: Discover agents but only load specific ones

agents:
  dirs:
    - ./agents  # Contains: zen-architect, bug-hunter, test-coverage, refactor-architect
  include-only:
    - zen-architect
    - bug-hunter
```
**Result:** Discovers from ./agents but ONLY loads zen-architect and bug-hunter.

### Example 3: Mixed Explicit and Discovery
```yaml
# profiles/base.yaml
profile:
  name: base
  version: 1.0.0
  description: Base profile with explicit agents and discovery

session:
  orchestrator:
    module: loop-streaming
    source: git+https://...
  context:
    module: context-enhanced
    source: git+https://...

agents:
  items:
    - name: zen-architect
      source: git+https://example.com/zen-architect@main
    - name: bug-hunter
      source: git+https://example.com/bug-hunter@main
  dirs:
    - ./agents  # Also discovers any other agents in this directory
```
**Result:** zen-architect and bug-hunter from explicit items PLUS any agents discovered in ./agents.

### Example 4: Development Profile (Selective Inheritance)
```yaml
# profiles/dev.yaml
profile:
  name: dev
  version: 1.0.0
  extends: base  # base has dirs: [./agents]
  description: Development profile with focused agents

agents:
  items:
    - name: refactor-architect
      source: git+https://example.com/refactor-architect@main
  include-only:
    - zen-architect
    - bug-hunter
    - refactor-architect
  # Inherits dirs from base: ./agents
```
**Result:** Discovers from ./agents (inherited), adds refactor-architect, filters to only 3 agents.

### Example 5: Production Profile (Discovery + Filter)
```yaml
# profiles/prod.yaml
profile:
  name: prod
  version: 1.0.0
  extends: base  # base has dirs: [./agents]
  description: Production profile with minimal agents

agents:
  include-only:
    - bug-hunter
  # Inherits dirs from base, but filters to only bug-hunter
```
**Result:** Discovers from ./agents but ONLY loads bug-hunter.

### Example 6: Custom Project Profile
```yaml
# profiles/my-project.yaml
profile:
  name: my-project
  version: 1.0.0
  extends: dev
  description: Project-specific profile

agents:
  items:
    - name: project-specialist
      source: file://./local-agents/project-specialist
  dirs:
    - ./project-agents
  # Inherits include-only from dev, adds new agent and directory
```
**Result:** Inherits filtered agents from dev, adds project-specialist, discovers from additional directory.

### Example 7: Agent-Free Profile
```yaml
# profiles/minimal.yaml
profile:
  name: minimal
  version: 1.0.0
  extends: base
  description: No agents, just core functionality

agents: []
```
**Result:** NO agents at all (complete reset).

## Key Points

1. **Omit agents key** = Inherit everything from parent
2. **agents: []** = Reset to nothing (no agents, no dirs)
3. **items** merge by name (child can add or override)
4. **dirs** append (child adds to parent's list)
5. **include-only** filters (child overrides parent's filter)
6. **include-only applies AFTER merging** (merge first, then filter)

## Migration from Old Structure

If you have old-style agents configuration:
```yaml
# OLD (don't use)
agents:
  - name: zen-architect
  - name: bug-hunter
```

Change to:
```yaml
# NEW
agents:
  items:
    - name: zen-architect
    - name: bug-hunter
```
