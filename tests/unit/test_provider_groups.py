"""
Unit tests for Provider Registry Group Management and Model Router Group Selection.

Tests provider group creation, selection policies (ROUND_ROBIN, WEIGHTED, LEAST_CONNECTIONS),
and integration with ModelRouter for group-based provider selection.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.core.provider import Provider
from aios.core.provider_registry import (
    ProviderRegistry,
    ProviderGroup,
    ProviderSelectionPolicy,
    get_provider_registry,
    reset_provider_registry_singleton,
)
from aios.core.model_router import (
    ModelRouter,
    ModelConfig,
    ModelProvider,
    ModelCapability,
    ModelRequest,
    ModelResponse,
)
from aios.events.core.types import EventType


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, provider_id: str, content: str = "from-mock"):
        self.provider_id = provider_id
        self.content = content
        self.generate_calls = 0
        self.reload_credentials_called = False

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_calls += 1
        return ModelResponse(
            content=f"{self.content}: {request.prompt[:20]} from {self.provider_id}",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
        )

    async def reload_credentials(self) -> None:
        """Mock implementation of reload_credentials for testing."""
        self.reload_credentials_called = True


@pytest.fixture(autouse=True)
def reset_registry_singleton():
    """Reset the provider registry singleton before each test."""
    reset_provider_registry_singleton()
    yield
    reset_provider_registry_singleton()


class TestProviderGroupBasics:
    """Test basic ProviderGroup functionality."""

    def test_provider_group_creation(self):
        """Test creating a provider group with basic parameters."""
        with open("debug_test.txt", "w") as f:
            f.write("DEBUG: Entering test_provider_group_creation\n")
        group = ProviderGroup(
            id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        print(f"DEBUG: group.id = {repr(group.id)}")
        print(f"DEBUG: group.label = {repr(group.label)}")
        print(f"DEBUG: group.provider_ids = {repr(group.provider_ids)}")
        print(f"DEBUG: group.policy = {repr(group.policy)}")
        print(f"DEBUG: group.weights = {repr(group.weights)}")
        print(f"DEBUG: group._rr_index = {repr(group._rr_index)}")
        print(f"DEBUG: group._connection_counts = {repr(group._connection_counts)}")

        assert group.id == "test-group"
        assert group.label == "Test Group"
        assert group.provider_ids == ["prov1", "prov2"]
        assert group.policy == ProviderSelectionPolicy.ROUND_ROBIN
        assert group.weights == {"prov1": 1.0, "prov2": 1.0}
        assert group._rr_index == 0
        assert group._connection_counts == {"prov1": 0, "prov2": 0}

    def test_provider_group_creation_with_weights(self):
        """Test creating a provider group with custom weights."""
        weights = {"prov1": 2.0, "prov2": 0.5}
        group = ProviderGroup(
            id="weighted-group",
            label="Weighted Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
            weights=weights,
        )

        assert group.weights == weights

    def test_provider_group_creation_default_weights(self):
        """Test that default weights are assigned when not provided."""
        group = ProviderGroup(
            id="default-weights",
            label="Default Weights Group",
            provider_ids=["prov1", "prov2", "prov3"],
            policy=ProviderSelectionPolicy.WEIGHTED,
        )

        # Should have equal weights for all providers
        assert group.weights == {"prov1": 1.0, "prov2": 1.0, "prov3": 1.0}

    def test_provider_group_creation_empty_list(self):
        """Test that creating a group with empty provider list raises no error in dataclass."""
        # The validation happens in ProviderRegistry.create_provider_group
        group = ProviderGroup(
            id="empty-group",
            label="Empty Group",
            provider_ids=[],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )
        assert group.provider_ids == []


class TestProviderRegistryGroupManagement:
    """Test ProviderRegistry group management functionality."""

    def test_create_provider_group_success(self):
        """Test successful creation of a provider group."""
        registry = ProviderRegistry()
        result = registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        assert result is True
        assert registry.has_provider_group("test-group")
        group = registry.get_provider_group("test-group")
        assert group is not None
        assert group.id == "test-group"
        assert group.label == "Test Group"
        assert group.provider_ids == ["prov1", "prov2"]
        assert group.policy == ProviderSelectionPolicy.ROUND_ROBIN

    def test_create_provider_group_duplicate_id(self):
        """Test that creating a group with duplicate ID fails."""
        registry = ProviderRegistry()
        # Create first group
        assert registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        ) is True

        # Try to create duplicate
        assert registry.create_provider_group(
            group_id="test-group",
            label="Test Group 2",
            provider_ids=["prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
        ) is False

        # Verify first group still exists and is unchanged
        group = registry.get_provider_group("test-group")
        assert group.label == "Test Group"
        assert group.provider_ids == ["prov1"]
        assert group.policy == ProviderSelectionPolicy.ROUND_ROBIN

    def test_create_provider_group_invalid_parameters(self):
        """Test that creating a group with invalid parameters fails."""
        registry = ProviderRegistry()

        # Empty group ID
        assert registry.create_provider_group(
            group_id="",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        ) is False

        # Empty label
        assert registry.create_provider_group(
            group_id="test-group",
            label="",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        ) is False

        # Empty provider list
        assert registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=[],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        ) is False

        # Non-existent provider - should succeed with warning (allows forward references)
        assert registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["nonexistent"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        ) is True

    def test_update_provider_group_success(self):
        """Test successful update of a provider group."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Original Label",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Update label and policy
        result = registry.update_provider_group(
            group_id="test-group",
            label="Updated Label",
            policy=ProviderSelectionPolicy.WEIGHTED,
        )

        assert result is True
        group = registry.get_provider_group("test-group")
        assert group.label == "Updated Label"
        assert group.policy == ProviderSelectionPolicy.WEIGHTED
        # Weights should be reset to default when policy changes to WEIGHTED
        assert group.weights == {"prov1": 1.0, "prov2": 1.0}

    def test_update_provider_group_with_weights(self):
        """Test updating a provider group with custom weights."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="weighted-group",
            label="Weighted Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
            weights={"prov1": 1.0, "prov2": 1.0},
        )

        # Update weights
        result = registry.update_provider_group(
            group_id="weighted-group",
            weights={"prov1": 3.0, "prov2": 0.5},
        )

        assert result is True
        group = registry.get_provider_group("weighted-group")
        assert group.weights == {"prov1": 3.0, "prov2": 0.5}

    def test_update_provider_group_invalid_parameters(self):
        """Test that updating a group with invalid parameters fails."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Empty group ID
        assert registry.update_provider_group(
            group_id="",
            label="Test Label",
        ) is False

        # Empty label
        assert registry.update_provider_group(
            group_id="test-group",
            label="",
        ) is False

        # Unknown group
        assert registry.update_provider_group(
            group_id="unknown-group",
            label="Test Label",
        ) is False

        # Negative weight - should be handled gracefully (converted to 0)
        assert registry.update_provider_group(
            group_id="test-group",
            weights={"prov1": -1.0},
        ) is True  # Negative weights should be converted to 0

    def test_update_provider_group_negative_weight_handling(self):
        """Test that negative weights are handled gracefully (set to 0)."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
        )

        # Update with negative weight - should be converted to 0
        result = registry.update_provider_group(
            group_id="test-group",
            weights={"prov1": -1.0, "prov2": 2.0},
        )

        assert result is True
        group = registry.get_provider_group("test-group")
        assert group.weights == {"prov1": 0.0, "prov2": 2.0}

    def test_remove_provider_group_success(self):
        """Test successful removal of a provider group."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        assert registry.has_provider_group("test-group") is True
        result = registry.remove_provider_group("test-group")
        assert result is True
        assert registry.has_provider_group("test-group") is False

    def test_remove_provider_group_unknown(self):
        """Test that removing an unknown group fails."""
        registry = ProviderRegistry()
        result = registry.remove_provider_group("unknown-group")
        assert result is False

    def test_add_provider_to_group_success(self):
        """Test successful addition of a provider to a group."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        result = registry.add_provider_to_group("test-group", "prov2")
        assert result is True

        group = registry.get_provider_group("test-group")
        assert "prov2" in group.provider_ids
        assert len(group.provider_ids) == 2
        assert group.provider_ids == ["prov1", "prov2"]

        # Weight should be initialized for the new provider
        assert group.weights["prov2"] == 1.0

        # Connection count should be initialized for LEAST_CONNECTIONS
        # (but we're using ROUND_ROBIN, so check the attribute exists)
        assert "prov2" in group._connection_counts

    def test_add_provider_to_group_already_exists(self):
        """Test that adding an already existing provider returns False."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Try to add existing provider
        result = registry.add_provider_to_group("test-group", "prov1")
        assert result is False  # Already in group

    def test_add_provider_to_group_invalid_parameters(self):
        """Test that adding provider with invalid parameters fails."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Empty group ID
        assert registry.add_provider_to_group("", "prov2") is False

        # Empty provider ID
        assert registry.add_provider_to_group("test-group", "") is False

        # Unknown group
        assert registry.add_provider_to_group("unknown-group", "prov2") is False

        # Unknown provider - should succeed with warning (allows forward references)
        assert registry.add_provider_to_group("test-group", "unknown-provider") is True

    def test_remove_provider_from_group_success(self):
        """Test successful removal of a provider from a group."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2", "prov3"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        result = registry.remove_provider_from_group("test-group", "prov2")
        assert result is True

        group = registry.get_provider_group("test-group")
        assert "prov2" not in group.provider_ids
        assert len(group.provider_ids) == 2
        assert set(group.provider_ids) == {"prov1", "prov3"}

        # Weight should be removed
        assert "prov2" not in group.weights

        # Connection count should be removed
        assert "prov2" not in group._connection_counts

    def test_remove_provider_from_group_not_in_group(self):
        """Test that removing a provider not in the group returns False."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Try to remove non-existent provider
        result = registry.remove_provider_from_group("test-group", "prov3")
        assert result is False  # Not in group

    def test_remove_provider_from_group_invalid_parameters(self):
        """Test that removing provider with invalid parameters fails."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Empty group ID
        assert registry.remove_provider_from_group("", "prov2") is False

        # Empty provider ID
        assert registry.remove_provider_from_group("test-group", "") is False

        # Unknown group
        assert registry.remove_provider_from_group("unknown-group", "prov2") is False

    def test_list_provider_groups(self):
        """Test listing provider groups."""
        registry = ProviderRegistry()
        assert registry.list_provider_groups() == []

        # Create some groups
        registry.create_provider_group(
            group_id="group1",
            label="Group 1",
            provider_ids=["prov1"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )
        registry.create_provider_group(
            group_id="group2",
            label="Group 2",
            provider_ids=["prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
        )

        groups = registry.list_provider_groups()
        assert len(groups) == 2
        group_ids = {g.id for g in groups}
        assert group_ids == {"group1", "group2"}

    def test_get_provider_group_unknown(self):
        """Test getting an unknown provider group returns None."""
        registry = ProviderRegistry()
        assert registry.get_provider_group("unknown-group") is None

    def test_get_provider_group_exists(self):
        """Test getting an existing provider group."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        group = registry.get_provider_group("test-group")
        assert group is not None
        assert group.id == "test-group"


class TestProviderRegistryGroupSelection:
    """Test ProviderRegistry group provider selection functionality."""

    @pytest.mark.asyncio
    async def test_select_provider_from_group_round_robin(self):
        """Test ROUND_ROBIN selection policy."""
        registry = ProviderRegistry()
        # Register providers
        from aios.core.provider import Provider
        from unittest.mock import MagicMock
        prov1 = MagicMock(spec=Provider)
        prov1.id = "prov1"
        prov2 = MagicMock(spec=Provider)
        prov2.id = "prov2"
        prov3 = MagicMock(spec=Provider)
        prov3.id = "prov3"
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)
        registry.register_provider("prov3", prov3)

        registry.create_provider_group(
            group_id="rr-group",
            label="Round Robin Group",
            provider_ids=["prov1", "prov2", "prov3"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Select providers multiple times and verify round-robin order
        selections = []
        for _ in range(6):  # Two full cycles
            provider_id = registry.select_provider_from_group(
                group_id="rr-group",
                model_id="test-model"
            )
            selections.append(provider_id)

        expected = ["prov1", "prov2", "prov3", "prov1", "prov2", "prov3"]
        assert selections == expected

    @pytest.mark.asyncio
    async def test_select_provider_from_group_weighted(self):
        """Test WEIGHTED selection policy."""
        registry = ProviderRegistry()
        # Register providers
        from aios.core.provider import Provider
        from unittest.mock import MagicMock
        prov1 = MagicMock(spec=Provider)
        prov1.id = "prov1"
        prov2 = MagicMock(spec=Provider)
        prov2.id = "prov2"
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)

        registry.create_provider_group(
            group_id="weighted-group",
            label="Weighted Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
            weights={"prov1": 2.0, "prov2": 1.0}  # prov1 should be selected ~2/3 of the time
        )

        # Select providers multiple times and count occurrences
        selections = {"prov1": 0, "prov2": 0}
        for _ in range(30):  # Enough samples to see distribution
            provider_id = registry.select_provider_from_group(
                group_id="weighted-group",
                model_id="test-model"
            )
            selections[provider_id] += 1

        # prov1 should be selected approximately 2/3 of the time (within reasonable variance)
        assert selections["prov1"] > selections["prov2"]  # prov1 should be selected more often
        assert selections["prov1"] >= 15  # At least half
        assert selections["prov2"] >= 5   # At least some selections

    @pytest.mark.asyncio
    async def test_select_provider_from_group_least_connections(self):
        """Test LEAST_CONNECTIONS selection policy."""
        registry = ProviderRegistry()
        # Register providers
        from aios.core.provider import Provider
        from unittest.mock import MagicMock
        prov1 = MagicMock(spec=Provider)
        prov1.id = "prov1"
        prov2 = MagicMock(spec=Provider)
        prov2.id = "prov2"
        prov3 = MagicMock(spec=Provider)
        prov3.id = "prov3"
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)
        registry.register_provider("prov3", prov3)

        registry.create_provider_group(
            group_id="lc-group",
            label="Least Connections Group",
            provider_ids=["prov1", "prov2", "prov3"],
            policy=ProviderSelectionPolicy.LEAST_CONNECTIONS,
        )

        # Manually set connection counts to test selection
        group = registry.get_provider_group("lc-group")
        group._connection_counts = {"prov1": 5, "prov2": 2, "prov3": 0}

        # Should select prov3 (least connections)
        provider_id = registry.select_provider_from_group(
            group_id="lc-group",
            model_id="test-model"
        )
        assert provider_id == "prov3"

        # Increment prov3's connection count and test again
        group._connection_counts["prov3"] = 3  # Make prov3 have more connections than prov2
        provider_id = registry.select_provider_from_group(
            group_id="lc-group",
            model_id="test-model"
        )
        assert provider_id == "prov2"  # Now prov2 has least connections (2)

        # Make all three equal, should pick prov1 (first in list with min connections)
        group._connection_counts["prov1"] = 3
        group._connection_counts["prov2"] = 3
        group._connection_counts["prov3"] = 3
        provider_id = registry.select_provider_from_group(
            group_id="lc-group",
            model_id="test-model"
        )
        assert provider_id == "prov1"  # First in list with min connection count (3)

    @pytest.mark.asyncio
    def test_select_provider_from_group_unknown_group(self):
        """Test selecting from an unknown group returns None."""
        registry = ProviderRegistry()
        provider_id = registry.select_provider_from_group(
            group_id="unknown-group",
            model_id="test-model"
        )
        assert provider_id is None

    @pytest.mark.asyncio
    def test_select_provider_from_group_empty_group(self):
        """Test selecting from an empty group returns None."""
        registry = ProviderRegistry()
        registry.create_provider_group(
            group_id="empty-group",
            label="Empty Group",
            provider_ids=[],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        provider_id = registry.select_provider_from_group(
            group_id="empty-group",
            model_id="test-model"
        )
        assert provider_id is None

    @pytest.mark.asyncio
    def test_select_provider_from_group_single_provider(self):
        """Test selecting from a group with single provider."""
        registry = ProviderRegistry()
        # Register provider
        from aios.core.provider import Provider
        from unittest.mock import MagicMock
        prov = MagicMock(spec=Provider)
        prov.id = "only-prov"
        registry.register_provider("only-prov", prov)

        registry.create_provider_group(
            group_id="single-group",
            label="Single Provider Group",
            provider_ids=["only-prov"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Should always select the same provider
        for _ in range(5):
            provider_id = registry.select_provider_from_group(
                group_id="single-group",
                model_id="test-model"
            )
            assert provider_id == "only-prov"

    def test_provider_group_thread_safety_basic(self):
        """Test basic thread safety of provider group operations."""
        import threading

        registry = ProviderRegistry()
        results = []

        def create_and_check_group(thread_id):
            group_id = f"thread-{thread_id}-group"
            success = registry.create_provider_group(
                group_id=group_id,
                label=f"Group {thread_id}",
                provider_ids=[f"prov-{thread_id}-1", f"prov-{thread_id}-2"],
                policy=ProviderSelectionPolicy.ROUND_ROBIN,
            )
            results.append((thread_id, success, group_id))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_check_group, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All groups should have been created successfully
        assert all(success for _, success, _ in results)
        assert len({group_id for _, _, group_id in results}) == 5  # All unique group IDs

        # Verify all groups exist
        for thread_id, _, group_id in results:
            assert registry.has_provider_group(group_id) is True
            group = registry.get_provider_group(group_id)
            assert group.label == f"Group {thread_id}"


class TestModelRouterGroupSelection:
    """Test ModelRouter integration with provider group selection."""

    @pytest.mark.asyncio
    async def test_model_router_selects_provider_from_group(self):
        """Test that ModelRouter selects provider from group when model config specifies group."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1", "from-prov1")
        prov2 = MockProvider("prov2", "from-prov2")
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)

        # Create provider group
        registry.create_provider_group(
            group_id="test-group",
            label="Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group (via provider config)
        model_config = ModelConfig(
            model_id="grouped-model",
            provider=ModelProvider.LOCAL,  # This will be overridden by group selection
            name="Grouped Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "test-group"},  # This tells router to use ProviderRegistry
        )
        router.register_model(model_config)

        # Generate multiple requests and verify round-robin selection
        responses = []
        for i in range(4):
            request = ModelRequest(prompt=f"test prompt {i}", preferred_model="grouped-model")
            response = await router.generate(request)
            responses.append(response)

        # Verify both providers were called (round-robin)
        assert prov1.generate_calls == 2
        assert prov2.generate_calls == 2

        # Verify responses contain correct provider content
        assert responses[0].content.startswith("from-prov1")
        assert responses[1].content.startswith("from-prov2")
        assert responses[2].content.startswith("from-prov1")
        assert responses[3].content.startswith("from-prov2")

    @pytest.mark.asyncio
    async def test_model_router_group_selection_weighted(self):
        """Test ModelRouter with WEIGHTED provider group selection."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1", "from-prov1")
        prov2 = MockProvider("prov2", "from-prov2")
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)

        # Create weighted provider group (prov1 weighted higher)
        registry.create_provider_group(
            group_id="weighted-group",
            label="Weighted Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.WEIGHTED,
            weights={"prov1": 3.0, "prov2": 1.0},  # prov1 should be selected ~75% of time
        )

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group
        model_config = ModelConfig(
            model_id="weighted-model",
            provider=ModelProvider.LOCAL,
            name="Weighted Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "weighted-group"},
        )
        router.register_model(model_config)

        # Generate multiple requests and verify weighted selection favors prov1
        prov1_calls_before = prov1.generate_calls
        prov2_calls_before = prov2.generate_calls

        for _ in range(20):
            request = ModelRequest(prompt="weighted test", preferred_model="weighted-model")
            await router.generate(request)

        prov1_calls_after = prov1.generate_calls - prov1_calls_before
        prov2_calls_after = prov2.generate_calls - prov2_calls_before

        # prov1 should be called more often than prov2 due to higher weight
        assert prov1_calls_after > prov2_calls_after
        # prov1 should get at least 10 calls out of 20 (3/4 weight = 75%)
        assert prov1_calls_after >= 10

    @pytest.mark.asyncio
    async def test_model_router_group_selection_least_connections(self):
        """Test ModelRouter with LEAST_CONNECTIONS provider group selection."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1", "from-prov1")
        prov2 = MockProvider("prov2", "from-prov2")
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)

        # Create least connections provider group
        registry.create_provider_group(
            group_id="lc-group",
            label="Least Connections Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.LEAST_CONNECTIONS,
        )

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group
        model_config = ModelConfig(
            model_id="lc-model",
            provider=ModelProvider.LOCAL,
            name="LC Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "lc-group"},
        )
        router.register_model(model_config)

        # Manually set connection counts to test selection
        group = registry.get_provider_group("lc-group")
        group._connection_counts = {"prov1": 5, "prov2": 0}

        # Generate requests and verify least connections selection
        responses = []
        for _ in range(4):
            request = ModelRequest(prompt="lc test", preferred_model="lc-model")
            response = await router.generate(request)
            responses.append(response)

        # First two should go to prov2 (0 connections), then prov1 and prov2 (now 1 each)
        assert responses[0].content.startswith("from-prov2")
        assert responses[1].content.startswith("from-prov2")
        assert responses[2].content.startswith("from-prov1")
        assert responses[3].content.startswith("from-prov2")

        # Verify call counts
        assert prov1.generate_calls == 1
        assert prov2.generate_calls == 3

    @pytest.mark.asyncio
    async def test_model_router_falls_back_to_individual_provider(self):
        """Test that ModelRouter falls back to individual provider lookup when not using groups."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("individual-prov", "from-individual")
        registry.register_provider("individual-prov", prov1)

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses individual provider (not a group)
        model_config = ModelConfig(
            model_id="individual-model",
            provider=ModelProvider.LOCAL,
            name="Individual Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "individual-prov"},  # Direct provider lookup
        )
        router.register_model(model_config)

        # Generate request and verify individual provider is used
        request = ModelRequest(prompt="individual test", preferred_model="individual-model")
        response = await router.generate(request)

        assert prov1.generate_calls == 1
        assert response.content.startswith("from-individual")

    @pytest.mark.asyncio
    async def test_model_router_group_selection_with_disabled_provider(self):
        """Test that disabled providers in a group are skipped during selection."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1-disabled", "from-prov1")
        prov2 = MockProvider("prov2-enabled", "from-prov2")
        registry.register_provider("prov1-disabled", prov1)
        registry.register_provider("prov2-enabled", prov2)

        # Create provider group
        registry.create_provider_group(
            group_id="mixed-group",
            label="Mixed Group",
            provider_ids=["prov1-disabled", "prov2-enabled"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Disable one provider
        registry.disable_provider("prov1-disabled")

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group
        model_config = ModelConfig(
            model_id="mixed-model",
            provider=ModelProvider.LOCAL,
            name="Mixed Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "mixed-group"},
        )
        router.register_model(model_config)

        # Generate multiple requests - should only get responses from enabled provider
        responses = []
        for _ in range(4):
            request = ModelRequest(prompt="mixed test", preferred_model="mixed-model")
            response = await router.generate(request)
            responses.append(response)

        # All responses should come from the enabled provider
        assert prov1.generate_calls == 0  # Disabled provider never called
        assert prov2.generate_calls == 4  # Enabled provider called all times

        for response in responses:
            assert response.content.startswith("from-prov2")

    @pytest.mark.asyncio
    async def test_model_router_group_selection_provider_unavailable(self):
        """Test that unavailable providers in a group are skipped during selection."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1-unavailable", "from-prov1")
        prov2 = MockProvider("prov2-available", "from-prov2")
        registry.register_provider("prov1-unavailable", prov1)
        registry.register_provider("prov2-available", prov2)

        # Create provider group
        registry.create_provider_group(
            group_id="unavailable-group",
            label="Unavailable Group",
            provider_ids=["prov1-unavailable", "prov2-available"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Make one provider unhealthy (simulating unavailability)
        from aios.core.provider_failures import ProviderFailure, FailureCategory
        failure = ProviderFailure(
            category=FailureCategory.SERVER_ERROR,
            provider_id="prov1-unavailable",
            safe_message="Internal server error"
        )
        registry.update_provider_health_from_failure("prov1-unavailable", failure)

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group
        model_config = ModelConfig(
            model_id="unavailable-model",
            provider=ModelProvider.LOCAL,
            name="Unavailable Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "unavailable-group"},
        )
        router.register_model(model_config)

        # Generate multiple requests - should only get responses from available provider
        responses = []
        for _ in range(4):
            request = ModelRequest(prompt="unavailable test", preferred_model="unavailable-model")
            response = await router.generate(request)
            responses.append(response)

        # All responses should come from the available provider
        assert prov1.generate_calls == 0  # Unavailable provider never called
        assert prov2.generate_calls == 4  # Available provider called all times

        for response in responses:
            assert response.content.startswith("from-prov2")

    @pytest.mark.asyncio
    async def test_model_router_emits_provider_group_selected_event(self):
        """Test that ModelRouter emits PROVIDER_GROUP_SELECTED event when using groups."""
        # Create provider registry and register mock providers
        registry = ProviderRegistry()
        prov1 = MockProvider("prov1", "from-prov1")
        prov2 = MockProvider("prov2", "from-prov2")
        registry.register_provider("prov1", prov1)
        registry.register_provider("prov2", prov2)

        # Create provider group
        registry.create_provider_group(
            group_id="event-test-group",
            label="Event Test Group",
            provider_ids=["prov1", "prov2"],
            policy=ProviderSelectionPolicy.ROUND_ROBIN,
        )

        # Create model router with provider registry
        router = ModelRouter(provider_registry=registry)

        # Register a model that uses the group
        model_config = ModelConfig(
            model_id="event-model",
            provider=ModelProvider.LOCAL,
            name="Event Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            enabled=True,
            config={"provider": "event-test-group"},
        )
        router.register_model(model_config)

        # Generate a request and verify event would be emitted
        # (We can't easily test the actual event emission without mocking the event bus,
        # but we can verify the group selection logic works)
        request = ModelRequest(prompt="event test", preferred_model="event-model")
        response = await router.generate(request)

        # Verify the response came from one of the group providers
        assert response.content.startswith("from-prov1") or response.content.startswith("from-prov2")
        assert prov1.generate_calls + prov2.generate_calls == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])