#!/usr/bin/env python3
"""
Simple test to debug MCP communication
"""
import asyncio
import json
import subprocess
import sys

async def simple_test():
    print("🔧 Starting simple MCP test...")
    
    try:
        # Start the MCP server
        print("🚀 Starting MCP server...")
        process = await asyncio.create_subprocess_exec(
            'node', '../dist/index.js', '../my_doc_index',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print("📤 Sending initialize request...")
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        request_json = json.dumps(init_request) + '\n'
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        print("📥 Waiting for response...")
        
        # Try to read response with timeout
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            if response_line:
                response_text = response_line.decode().strip()
                print(f"✅ Got response: {response_text}")
                
                try:
                    response = json.loads(response_text)
                    print(f"✅ Parsed response: {response}")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error: {e}")
            else:
                print("❌ No response received")
        except asyncio.TimeoutError:
            print("❌ Response timeout")
        
        # Test tools list
        print("📤 Sending tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        request_json = json.dumps(tools_request) + '\n'
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        print("📥 Waiting for tools response...")
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            if response_line:
                response_text = response_line.decode().strip()
                print(f"✅ Tools response: {response_text}")
        except asyncio.TimeoutError:
            print("❌ Tools response timeout")
        
        # Test a tool call
        print("📤 Sending catalog_search tool call...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "catalog_search",
                "arguments": {"text": "healthcare"}
            }
        }
        
        request_json = json.dumps(tool_request) + '\n'
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        print("📥 Waiting for tool call response...")
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            if response_line:
                response_text = response_line.decode().strip()
                print(f"✅ Tool call response: {response_text[:200]}...")
        except asyncio.TimeoutError:
            print("❌ Tool call response timeout")
        
        # Check stderr for any errors
        try:
            stderr_data = await asyncio.wait_for(process.stderr.read(1024), timeout=1.0)
            if stderr_data:
                print(f"🔍 Server stderr: {stderr_data.decode()}")
        except asyncio.TimeoutError:
            pass
        
        # Cleanup
        process.terminate()
        await process.wait()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test())