# FINAL EXTERNAL OPERATIONAL TEST PLAN

**AI-OS · Gated External Integration Test Plan**
**Date:** 2026-08-27
**Author:** Terminal 1 — Architecture/Planning Authority

## 1. TESTING PHILOSOPHY

Real external tests MUST:
- Never run in ordinary regression (require explicit opt-in)
- Never expose credentials or persist secrets
- Record provenance and integration/service/version information
- Distinguish real vs mock execution clearly
- Fail closed - never alter authoritative AI-OS state unexpectedly
- Always route through SecurityManager validation gates

## 2. TEST MARKERS

Use compatible markers with repository conventions:
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.requires_env("INTEGRATION_NAME_ENABLED")
```

## 3. MINIMUM REAL OPERATION REQUIREMENTS

Each integration must demonstrate the minimum viable real operation:

### 3.1 EXECUTION
#### Hermes/ACP
- Real hermes-agent subprocess execution returning structured observation
- ACP initialize handshake completion
- Worker session lifecycle management
- Provenance attached to all observations

#### Playwright MCP
- Real browser navigation to approved domain
- DOM interaction (click, type, screenshot)
- Context isolation and cleanup
- Secret redaction in traces/logs

#### MCP Generic
- Real stdio MCP server connection
- Tool discovery and execution
- Resource reading (if supported)
- Proper stdio transport handling

### 3.2 KNOWLEDGE
#### Obsidian
- Real vault read of controlled test artifact (frontend matter preserved)
- Real vault write of controlled test artifact
- Wikilink resolution and frontend matter handling
- filesystem sync vs MCP consistency (if both enabled)

#### Graphify
- Real node/edge creation in isolated namespace
- Real graph query returning expected results
- Real node/edge update/delete operations
- Namespace isolation verification

#### Claude-Mem
- Real contextual memory storage and retrieval
- Tag-based memory organization
- Temporal memory querying
- Advisory-only verification (no decision authority)

### 3.3 PLANNING
#### Notion
- Real page/database read operation
- Controlled test-page creation/update
- Property and relationship handling
- Comment and discussion retrieval

### 3.4 MODEL INFRASTRUCTURE
#### FreeLLMAPI
- Real LLM generation request with controlled prompt
- Response validation and parsing
- Cost/performance tracking (where applicable)
- Dev/test only enforcement

## 4. INTEGRATION-SPECIFIC TESTS

### 4.1 HERMES/ACP TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.hermes_acp
def test_hermes_acp_real_execution():
    """Test real ACP execution with hermes-agent."""
    # Arrange
    hermes_bridge = get_hermes_bridge()
    assert hermes_bridge is not None
    
    # Act - Execute real task via ACP
    observation = await hermes_bridge.execute_task(
        prompt="Return structured observation: {{'test': 'value'}}",
        context={"test_isolation": True}
    )
    
    # Assert
    assert observation is not None
    assert "test" in observation.structured_data
    assert observation.provenance.worker == "hermes-agent-ext"
    assert observation.provenance.integration == "hermes_acp"
    assert not observation.authoritative  # Advisory only
    assert observation.trust_level == "contextual"
```

### 4.2 PLAYWRIGHT MCP TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.playwright
def test_playwright_real_browser_operation():
    """Test real Playwright browser operation."""
    # Arrange
    playwright_adapter = get_playwright_adapter()
    assert playwright_adapter is not None
    assert is_playwright_available()  # Node + @playwright/mcp + browser
    
    # Act - Real browser operation
    result = await playwright_adapter.execute_browser_task(
        task="navigate_and_snapshot",
        url="https://example.com/test",  # Approved domain
        actions=[
            {"action": "navigate", "url": "https://example.com/test"},
            {"action": "snapshot"},
            {"action": "screenshot"}
        ]
    )
    
    # Assert
    assert result is not None
    assert result.provenance.integration == "playwright_mcp"
    assert result.provenance.worker == "playwright-browser"
    assert not result.authoritative  # Advisory only
    assert "example.com" in str(result.artifacts)  # Domain allowlist verified
    # Secret redaction verified in logs/artifacts
```

### 4.3 OBSIDIAN TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.obsidian
def test_obsidian_real_vault_operation(tmp_path):
    """Test real Obsidian vault read/write operation."""
    # Arrange
    obsidian_adapter = get_obsidian_adapter()
    assert obsidian_adapter is not None
    test_vault = tmp_path / "test_vault"
    test_vault.mkdir()
    
    # Configure adapter with real test vault
    obsidian_adapter.configure_vault_path(str(test_vault))
    
    # Create test artifact
    test_file = test_vault / "test_note.md"
    test_file.write_text("---\ntags: [test, ai-os]\n---\n# Test Note\n\nThis is a test.")
    
    # Act - Real read operation
    note = await obsidian_adapter.get_note("test_note.md")
    
    # Assert
    assert note is not None
    assert note.title == "Test Note"
    assert note.content.contains("This is a test.")
    assert note.provenance.integration == "obsidian"
    assert note.provenance.vault_path == str(test_vault)
    assert not note.authoritative  # Advisory only
    
    # Act - Real write operation
    await obsidian_adapter.create_note(
        "test_write.md", 
        "---\ntags: [verification]\n---\n# Write Test\n\nSuccessfully written."
    )
    
    # Assert write succeeded
    written_file = test_vault / "test_write.md"
    assert written_file.exists()
    content = written_file.read_text()
    assert "# Write Test" in content
    assert "Successfully written." in content
```

### 4.4 GRAPHIFY TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.graphify
def test_graphify_real_graph_operations():
    """Test real Graphify graph operations."""
    # Arrange
    graphify_adapter = get_graphify_adapter()
    assert graphify_adapter is not None
    test_namespace = f"ai-os-test-{uuid4().hex[:8]}"
    
    # Act - Create nodes and edges
    node_a = await graphify_adapter.add_node(
        label="Test Node A",
        properties={"type": "test", "ai_os_generated": True},
        namespace=test_namespace
    )
    
    node_b = await graphify_adapter.add_node(
        label="Test Node B", 
        properties={"type": "test", "ai_os_generated": True},
        namespace=test_namespace
    )
    
    edge = await graphify_adapter.add_edge(
        source=node_a.id,
        target=node_b.id,
        label="RELATES_TO",
        properties={"ai_os_verified": True},
        namespace=test_namespace
    )
    
    # Assert creation
    assert node_a is not None
    assert node_b is not None
    assert edge is not None
    assert node_a.provenance.integration == "graphify"
    assert not node_a.authoritative  # Advisory only
    
    # Act - Query graph
    results = await graphify_adapter.query_graph(
        f"WHERE {{ ?n ai_os_generated: true }} RETURN ?n",
        namespace=test_namespace
    )
    
    # Assert query returned expected results
    assert len(results) >= 2
    assert all(not r.authoritative for r in results)  # All advisory
    
    # Act - Cleanup (important for isolation)
    await graphify_adapter.delete_node(node_a.id, namespace=test_namespace)
    await graphify_adapter.delete_node(node_b.id, namespace=test_namespace)
```

### 4.5 NOTION TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.notion
def test_notion_real_planning_operation():
    """Test real Notion planning operation."""
    # Arrange
    notion_adapter = get_notion_adapter()
    assert notion_adapter is not None
    
    # Act - Real database/query operation
    results = await notion_adapter.search_pages(
        query="ai-os-test-page",
        filter_properties={"object": "page"}
    )
    
    # Even if no results, verify we got real response
    assert results is not None
    assert hasattr(results, 'provenance')
    assert results.provenance.integration == "notion"
    assert not results.authoritative  # Advisory only
    # Would validate real endpoint connection here
    
    # Act - Create test page (if permissions allow)
    test_page = await notion_adapter.create_page(
        parent_id=get_test_parent_id(),
        properties={
            "Name": {"title": [{"text": {"content": "AI-OS Test Page"}}]},
            "Tags": {"multi_select": [{"name": "test"}, {"name": "ai-os"}]}
        },
        children=[{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "This is a test page for AI-OS verification."}}]
            }
        }]
    )
    
    # Assert creation succeeded
    assert test_page is not None
    assert test_page.id is not None
    assert not test_page.authoritative  # Advisory only
    
    # Cleanup
    await notion_adapter.archive_page(test_page.id)
```

### 4.6 FREELLM API TESTS
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.freellm
def test_freellm_real_generation():
    """Test real FreeLLMAPI generation."""
    # Arrange
    model_router = get_model_router()
    assert model_router is not None
    assert is_freellm_available()  # Server running, accessible
    
    # Act - Real generation request
    request = ModelRequest(
        prompt="Explain AI-OS architecture in one sentence.",
        max_tokens=50,
        temperature=0.7
    )
    
    response = await model_router.generate(request)
    
    # Assert
    assert response is not None
    assert response.model == "freellmapi-default"
    assert response.provider == ModelProvider.LOCAL
    assert len(response.text) > 0
    assert "AI-OS" in response.text or "architecture" in response.text.lower()
    assert not response.authoritative  # Advisory only
    assert response.cost == 0.0  # FreeLLMAPI is free
```

## 5. CROSS-INTEGRATION E2E TESTS

### 5.1 HERMES + PLAYWRIGHT
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.cross_integration
def test_hermes_playwright_e2e():
    """Test Hermes orchestrating Playwright browser operation."""
    # Arrange
    hermes_bridge = get_hermes_bridge()
    playwright_adapter = get_playwright_adapter()
    assert all([hermes_bridge, playwright_adapter])
    
    # Act - Hermes directs Playwright via structured task
    observation = await hermes_bridge.execute_task(
        prompt="""
        Use Playwright to:
        1. Navigate to https://example.com
        2. Take a screenshot
        3. Return structured data with URL and success status
        """,
        context={
            "playwright_available": True,
            "approved_domains": ["example.com"]
        }
    )
    
    # Assert
    assert observation is not None
    assert observation.provenance.integration == "hermes_acp"  # Or mcp fallback
    assert "playwright" in str(observation.artifacts).lower()
    assert not observation.authoritative
    
    # Verify Playwright actually executed
    assert observation.structured_data.get("url") == "https://example.com"
    assert observation.structured_data.get("success") is True
```

### 5.2 HERMES + GRAPHIFY + KNOWLEDGE
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.cross_integration
def test_hermes_graphify_obsidian_e2e():
    """Test Hermes coordinating Graphify and Obsidian knowledge work."""
    # Arrange
    hermes_bridge = get_hermes_bridge()
    graphify_adapter = get_graphify_adapter()
    obsidian_adapter = get_obsidian_adapter()
    assert all([hermes_bridge, graphify_adapter, obsidian_adapter])
    
    # Act - Hermes orchestrates knowledge workflow
    observation = await hermes_bridge.execute_task(
        prompt="""
        Knowledge workflow:
        1. Extract key concepts from Obsidian vault
        2. Create corresponding nodes in Graphify
        3. Link related concepts
        4. Return structured summary
        """,
        context={
            "vault_path": get_test_vault_path(),
            "namespace": f"ai-os-e2e-{uuid4().hex[:8]}"
        }
    )
    
    # Assert
    assert observation is not None
    assert observation.provenance.integration in ["hermes_acp", "hermes_mcp"]
    assert len(observation.artifacts) > 0
    assert not observation.authoritative
    
    # Verify both knowledge systems were used
    obsidian_used = any("obsidian" in str(a).lower() for a in observation.artifacts)
    graphify_used = any("graphify" in str(a).lower() or "node" in str(a).lower() 
                       for a in observation.artifacts)
    assert obsidian_used and graphify_used
```

## 6. FAILURE/DEGRADED MODE TESTS

### 6.1 SECURITY GATE FAILURE
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.security
def test_mcp_security_gate_enforcement():
    """Test that invalid MCP connections are blocked by SecurityManager."""
    # Arrange - Attempt to connect to untrusted/non-existent MCP server
    invalid_config = {
        "server_id": "invalid-server",
        "command": ["python", "-m", "non.existent.module"],
        "transport": "stdio"
    }
    
    # Act & Assert - Should fail at SecurityManager level
    with pytest.raises(SecurityError, match="MCP server validation failed"):
        await mcp_manager.connect_server(invalid_config)
    
    # Verify connection never established
    assert not mcp_manager.is_connected("invalid-server")
```

### 6.2 MCP FALLBACK WHEN ACP UNAVAILABLE
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.fallback
def test_hermes_acp_mcp_fallback():
    """Test Hermes gracefully falls back to MCP when ACP unavailable."""
    # Arrange - Disable ACP, enable MCP
    hermes_bridge = HermesBridge(
        protocol="acp",
        fallback_to_mcp=True,
        mcp_manager=get_mcp_manager(),
        server_id="hermes_agent_ext"
    )
    # Mock ACP as unavailable
    
    # Act
    observation = await hermes_bridge.execute_task(
        prompt="Return test observation",
        context={"test": True}
    )
    
    # Assert - Should succeed via MCP fallback
    assert observation is not None
    assert observation.provenance.integration == "hermes_mcp"  # Fallback used
    assert not observation.authoritative
    assert observation.trust_level == "contextual"
```

### 6.3 SINGLE INTEGRATION FAILURE
```python
@pytest.mark.gated
@pytest.mark.external
@pytest.mark.resilience
def test_multi_integration_degraded_mode():
    """Test system continues when one integration fails."""
    # Arrange - Mock Obsidian failure, others working
    with patch.object(get_obsidian_adapter(), 'get_note', 
                     side_effect=ConnectionError("Vault unavailable")):
        
        # Act - Attempt cross-integration workflow
        observation = await get_hermes_bridge().execute_task(
            prompt="Get knowledge from available sources",
            context={"require_obsidian": True}
        )
        
        # Assert - System should degrade gracefully
        assert observation is not None
        assert not observation.authoritative
        # Should still get data from Graphify or other sources
        assert len([a for a in observation.artifacts if a]) > 0
        # Should indicate Obsidian was unavailable in provenance
        assert any("obsidian" in str(a).lower() and "unavailable" in str(a).lower()
                  for a in observation.artifacts)
```

## 7. ENVIRONMENT VARIABLES FOR GATED TESTS

Set these to enable gated external tests:
```bash
# Individual integrations
HERMES_ACP_ENABLED=true
PLAYWRIGHT_ENABLED=true  
OBSIDIAN_ENABLED=true
GRAPHIFY_ENABLED=true
NOTION_ENABLED=true
FREELLM_ENABLED=true

# Cross-integration
CROSS_INTEGRATION_ENABLED=true

# Or enable all
EXTERNAL_INTEGRATIONS_ENABLED=true

# Specific configuration (examples)
OBSIDIAN_VAULT_PATH=/path/to/test/vault
NOTION_API_KEY=secret  # Never actually set in CI - use mock mode
PLAYWRIGHT_BROWSER=chromium
FREELLM_API_URL=http://localhost:8080
```

## 8. IMPLEMENTATION NOTES

### 8.1 Test Isolation
- All tests must use isolated namespaces/vaults/etc.
- Cleanup is mandatory after each test
- No cross-test state pollution allowed

### 8.2 Provenance Requirements
All test outputs must include:
- Integration name and version
- Worker/session identifiers  
- Timestamp and environment
- Trust level and authority designation
- Advisory flags where applicable

### 8.3 Secret Handling
- No credentials in test code or logs
- Environment variables only for configuration
- Secret redaction verified in all outputs
- Fail fast if secrets detected in unexpected places

### 8.4 External Service Requirements
Tests assume:
- Services are running and accessible
- Proper versions are installed
- Network connectivity exists
- Required accounts/permissions configured
- But NEVER assumes actual credentials are present in repo

---
*This test plan defines the minimum viable real operation for each integration while preserving AI-OS authority and security invariants.*