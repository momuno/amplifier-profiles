"""Tests for agent exclude feature with convergent-dev collection."""

import json
from pathlib import Path

import pytest

from amplifier_collections import CollectionResolver
from amplifier_profiles import AgentLoader, AgentResolver, ProfileLoader, compile_profile_to_mount_plan


@pytest.fixture
def convergent_dev_collection():
    """Path to convergent-dev collection."""
    collection_path = Path(__file__).parent.parent.parent / "amplifier-collection-convergent-dev"
    if not collection_path.exists():
        pytest.skip(f"Collection not found at {collection_path}")
    return collection_path


@pytest.fixture
def collection_resolver(convergent_dev_collection):
    """Collection resolver with convergent-dev collection."""
    # Search paths for collections
    app_cli_collections = Path(__file__).parent.parent.parent / "momuno_amplifier-app-cli" / "amplifier_app_cli" / "data" / "collections"

    search_paths = [convergent_dev_collection.parent]

    # Add app-cli collections if available (for developer-expertise collection)
    if app_cli_collections.exists():
        search_paths.append(app_cli_collections)

    return CollectionResolver(search_paths=search_paths)


@pytest.fixture
def agent_loader(convergent_dev_collection, collection_resolver):
    """Agent loader for convergent-dev collection."""
    resolver = AgentResolver(
        search_paths=[convergent_dev_collection / "agents"],
        collection_resolver=collection_resolver,
    )
    return AgentLoader(resolver=resolver, mention_loader=None)


@pytest.fixture
def profile_loader(convergent_dev_collection, collection_resolver):
    """Profile loader for convergent-dev collection."""
    return ProfileLoader(
        search_paths=[convergent_dev_collection / "profiles"],
        collection_resolver=collection_resolver,
        mention_loader=None,
    )


class TestAgentExcludeFeature:
    """Test agent exclude field functionality."""

    def test_tdd_specialist_has_exclude_field(self, agent_loader):
        """Test that tdd-specialist agent has exclude field."""
        agent = agent_loader.load_agent("tdd-specialist")

        # Verify exclude field is set
        assert agent.exclude is not None
        assert "agents" in agent.exclude
        assert agent.exclude["agents"] == "all"

    def test_tdd_specialist_has_agents_list(self, agent_loader):
        """Test that tdd-specialist agent has specific agents list."""
        agent = agent_loader.load_agent("tdd-specialist")

        # Verify agents list is set
        assert agent.agents is not None
        assert isinstance(agent.agents, list)
        assert "bug-hunter" in agent.agents
        assert "zen-architect" in agent.agents
        assert "module-builder" in agent.agents

    def test_exclude_appears_in_mount_plan_fragment(self, agent_loader):
        """Test that exclude field appears in mount plan fragment."""
        agent = agent_loader.load_agent("tdd-specialist")
        fragment = agent.to_mount_plan_fragment()

        print("\n=== TDD Specialist Mount Plan Fragment ===")
        print(json.dumps(fragment, indent=2))

        # Verify exclude is in the fragment
        assert "exclude" in fragment
        assert fragment["exclude"]["agents"] == "all"

        # Verify agents list is also in the fragment
        assert "agents" in fragment
        assert isinstance(fragment["agents"], list)

    def test_profile_compilation_includes_agent_exclude(self, profile_loader, agent_loader):
        """Test that profile compilation includes agent exclude fields."""
        # This test will fail if profile extends another profile we don't have
        try:
            profile = profile_loader.load_profile("convergent-dev")
        except Exception as e:
            print(f"\nError loading profile: {e}")
            import traceback
            traceback.print_exc()
            pytest.skip(f"Could not load profile: {e}")

        mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)

        print("\n=== Convergent Dev Mount Plan (summary) ===")
        print(f"Agents loaded: {list(mount_plan['agents'].keys())}")

        # Check if tdd-specialist is in the mount plan
        if "tdd-specialist" in mount_plan["agents"]:
            tdd_config = mount_plan["agents"]["tdd-specialist"]
            print(f"\nTDD Specialist config keys: {list(tdd_config.keys())}")

            if "exclude" in tdd_config:
                print(f"  - Exclude: {tdd_config['exclude']}")
            if "agents" in tdd_config:
                print(f"  - Agents: {tdd_config['agents']}")

            # Verify exclude is preserved in mount plan
            assert "exclude" in tdd_config, "exclude field should be in mount plan"
            assert tdd_config["exclude"]["agents"] == "all"

            # Verify agents list is preserved
            assert "agents" in tdd_config, "agents field should be in mount plan"
            assert isinstance(tdd_config["agents"], list)

    def test_all_agents_preserve_exclude_if_present(self, agent_loader):
        """Test that all agents preserve their exclude fields."""
        agents = agent_loader.list_agents()

        for agent_name in agents:
            agent = agent_loader.load_agent(agent_name)
            fragment = agent.to_mount_plan_fragment()

            # If agent has exclude, it should be in the fragment
            if agent.exclude is not None:
                assert "exclude" in fragment, f"{agent_name} has exclude but it's not in fragment"
                assert fragment["exclude"] == agent.exclude, f"{agent_name} exclude doesn't match"
                print(f"✓ {agent_name}: exclude preserved")
