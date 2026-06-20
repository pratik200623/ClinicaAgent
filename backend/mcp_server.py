import sys
import json
import asyncio
import logging
from typing import Dict, Any, List

# Add path so imports work correctly when run directly
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.clinical_agent import match_clinical_trials
from backend.agents.genomic_agent import interpret_genomic_variants
from backend.agents.literature_agent import search_literature
from backend.agents.intake_agent import PatientProfile

# Setup logging to stderr because stdout is used for JSON-RPC messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("mcp_server")

# Define tools
TOOLS = [
    {
        "name": "match_clinical_trials",
        "description": "Query ClinicalTrials.gov for active recruiting trials matching a condition and location.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Medical condition or disease (e.g. Non-Small Cell Lung Cancer)"
                },
                "location": {
                    "type": "string",
                    "description": "Optional geographic location/state (e.g. California)"
                }
            },
            "required": ["condition"]
        }
    },
    {
        "name": "interpret_genomic_variants",
        "description": "Queries ClinVar database for pathogenicity and details of specific genetic variants.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Primary condition (e.g. Lung Cancer)"
                },
                "variants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of variants to analyze (e.g. ['EGFR T790M'])"
                }
            },
            "required": ["variants"]
        }
    },
    {
        "name": "search_literature",
        "description": "Queries PubMed for recent treatment studies and medical literature.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Medical condition or disease"
                },
                "variants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of genetic variants to refine search"
                }
            },
            "required": ["condition"]
        }
    }
]

def send_response(response: Dict[str, Any]):
    """Send a JSON-RPC response to stdout followed by a newline."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

async def handle_request(req: Dict[str, Any]):
    """Processes a JSON-RPC request and sends the response."""
    method = req.get("method")
    req_id = req.get("id")
    
    # We only care about requests (which have ids). Notifications are ignored/handled separately.
    if req_id is None:
        return

    logger.info(f"Received request: method={method}, id={req_id}")

    try:
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ClinicaAgent-MCP",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            })
            
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Calling tool: {tool_name} with args: {arguments}")
            
            if tool_name == "match_clinical_trials":
                condition = arguments.get("condition")
                location = arguments.get("location")
                profile = PatientProfile(condition=condition, location=location, variants=[])
                res = await match_clinical_trials(profile)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res, indent=2)}
                        ]
                    }
                })
                
            elif tool_name == "interpret_genomic_variants":
                condition = arguments.get("condition", "Cancer")
                variants = arguments.get("variants", [])
                profile = PatientProfile(condition=condition, variants=variants)
                res = await interpret_genomic_variants(profile)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res, indent=2)}
                        ]
                    }
                })
                
            elif tool_name == "search_literature":
                condition = arguments.get("condition")
                variants = arguments.get("variants", [])
                profile = PatientProfile(condition=condition, variants=variants)
                res = await search_literature(profile)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res, indent=2)}
                        ]
                    }
                })
            else:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                })
        else:
            # Method not found
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            })
            
    except Exception as e:
        logger.exception(f"Error handling request {req_id}: {e}")
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        })

async def main():
    logger.info("ClinicaAgent MCP Server starting...")
    
    # Check if run loop can read from stdin asynchronously
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8').strip()
            if not line_str:
                continue
                
            req = json.loads(line_str)
            asyncio.create_task(handle_request(req))
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in read loop: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    logger.info("ClinicaAgent MCP Server stopped.")
