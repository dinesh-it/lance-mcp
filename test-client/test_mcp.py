#!/usr/bin/env python3
"""
Test script to debug MCP connection and tool calls
"""
import asyncio
import json
from mcp_client import MCPClient

async def test_mcp():
    print("🔍 Testing MCP connection...")
    
    client = MCPClient("../dist/index.js", "../my_doc_index")
    
    try:
        await client.connect()
        print("✅ Connected successfully!")
        
        # List available tools
        tools = client.get_available_tools()
        print(f"\n🛠️ Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
            print(f"    Schema: {tool.input_schema}")
        
        # Test catalog search
        print(f"\n🔍 Testing catalog_search...")
        try:
            result = await client.call_tool("catalog_search", {"query": "healthcare"})
            print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        except Exception as e:
            print(f"❌ catalog_search error: {e}")
        
        # Test chunks search
        print(f"\n🔍 Testing all_chunks_search...")
        try:
            result = await client.call_tool("all_chunks_search", {"query": "MyUsage"})
            print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        except Exception as e:
            print(f"❌ all_chunks_search error: {e}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_mcp())