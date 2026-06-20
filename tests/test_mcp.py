import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from backend.mcp_server import handle_request, TOOLS

@pytest.mark.asyncio
async def test_mcp_initialize():
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05"
        }
    }
    
    with patch("backend.mcp_server.send_response") as mock_send:
        await handle_request(request)
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response["id"] == 1
        assert response["result"]["serverInfo"]["name"] == "ClinicaAgent-MCP"
        assert response["result"]["protocolVersion"] == "2024-11-05"

@pytest.mark.asyncio
async def test_mcp_tools_list():
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    with patch("backend.mcp_server.send_response") as mock_send:
        await handle_request(request)
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response["id"] == 2
        assert len(response["result"]["tools"]) == len(TOOLS)
        assert response["result"]["tools"][0]["name"] == "match_clinical_trials"

@pytest.mark.asyncio
@patch("backend.mcp_server.match_clinical_trials")
async def test_mcp_tools_call_clinical_trials(mock_match):
    # Setup mock return value
    mock_match.return_value = [{"nct_id": "NCT0123", "title": "Mock Trial"}]
    
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "match_clinical_trials",
            "arguments": {
                "condition": "Lung Cancer",
                "location": "California"
            }
        }
    }
    
    with patch("backend.mcp_server.send_response") as mock_send:
        await handle_request(request)
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response["id"] == 3
        
        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        
        data = json.loads(content[0]["text"])
        assert data[0]["nct_id"] == "NCT0123"
        assert data[0]["title"] == "Mock Trial"
