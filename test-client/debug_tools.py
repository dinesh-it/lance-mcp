#!/usr/bin/env python3
"""
Debug script to test MCP tool calls directly
"""
import asyncio
from mcp_client import MCPClient

async def debug_tools():
    print("🔧 Testing MCP tool calls...")
    
    client = MCPClient("../dist/index.js", "../my_doc_index")
    
    try:
        print("🔗 Connecting...")
        await asyncio.wait_for(client.connect(), timeout=10.0)
        print("✅ Connected!")
        
        # Test simple catalog search first
        print(f"\n📋 Testing catalog_search with 'healthcare':")
        try:
            result = await asyncio.wait_for(
                client.call_tool("catalog_search", {"query": "healthcare"}), 
                timeout=15.0
            )
            print(f"✅ Catalog result: {result[:300]}..." if len(result) > 300 else result)
        except asyncio.TimeoutError:
            print("❌ Catalog search timed out")
        except Exception as e:
            print(f"❌ Catalog error: {e}")
        
        print(f"\n📄 Testing all_chunks_search with 'MyUsage':")
        try:
            result = await asyncio.wait_for(
                client.call_tool("all_chunks_search", {"query": "MyUsage"}), 
                timeout=15.0
            )
            print(f"✅ Chunks result: {result[:300]}..." if len(result) > 300 else result)
        except asyncio.TimeoutError:
            print("❌ Chunks search timed out")
        except Exception as e:
            print(f"❌ Chunks error: {e}")
            
    except asyncio.TimeoutError:
        print("❌ Connection timed out")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        try:
            await client.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(debug_tools())