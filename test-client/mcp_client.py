"""
MCP Client for connecting to the lance-mcp server
"""
import asyncio
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    def __init__(self, server_path: str, db_path: str):
        self.server_path = server_path
        self.db_path = db_path
        self.process = None
        self.available_tools: List[MCPTool] = []
        
    async def connect(self):
        """Start the MCP server process and connect to it"""
        try:
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                'node', self.server_path, self.db_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize the connection
            await self._send_request({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "python-chat-client",
                        "version": "1.0.0"
                    }
                }
            })
            
            # Get available tools
            await self._load_tools()
            
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            raise
    
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and get response"""
        if not self.process:
            raise RuntimeError("MCP server not connected")
            
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
            
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            print(f"Failed to parse response: {response_line}")
            raise e
    
    async def _load_tools(self):
        """Load available tools from the MCP server"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })
        
        if "result" in response and "tools" in response["result"]:
            for tool_data in response["result"]["tools"]:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["inputSchema"]
                )
                self.available_tools.append(tool)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on the MCP server"""
        response = await self._send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        
        if "result" in response:
            if "content" in response["result"]:
                # Extract text content from the response
                content = response["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    return content[0].get("text", "")
            return str(response["result"])
        elif "error" in response:
            return f"Error: {response['error']['message']}"
        else:
            return "No result returned"
    
    async def search_catalog(self, query: str) -> str:
        """Search the document catalog"""
        return await self.call_tool("catalog_search", {"text": query})
    
    async def search_chunks(self, query: str, source: Optional[str] = None) -> str:
        """Search document chunks"""
        if source:
            # chunks_search requires both text and source
            return await self.call_tool("chunks_search", {"text": query, "source": source})
        else:
            # all_chunks_search requires only text
            return await self.call_tool("all_chunks_search", {"text": query})
    
    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available tools"""
        return self.available_tools
    
    async def close(self):
        """Close the MCP server connection"""
        if self.process:
            self.process.terminate()
            await self.process.wait()