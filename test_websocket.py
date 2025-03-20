#!/usr/bin/env python3
"""
Simple WebSocket client to test the improved dataset WebSocket endpoint
"""

import asyncio
import websockets
import json

async def test_dataset_websocket():
    uri = "ws://localhost:8000/dataset/get"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send initial request with dataset names
            initial_request = {
                "names": ["SNP Transformed current"]
            }
            await websocket.send(json.dumps(initial_request))
            print(f"Sent initial request: {initial_request}")
            
            # Listen for responses
            async for message in websocket:
                response = json.loads(message)
                print(f"Received: {response}")
                
                # Break if we receive a final message
                if response.get("type") == "final":
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_dataset_websocket())
