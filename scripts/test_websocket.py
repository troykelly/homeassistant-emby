#!/usr/bin/env python3
"""Test script to explore Emby WebSocket API behavior.

This script connects to the Emby WebSocket API and logs all messages received
to help understand the exact message formats and event types.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

import aiohttp


async def test_websocket() -> None:
    """Connect to Emby WebSocket and log all messages."""
    emby_url = os.environ.get("EMBY_URL")
    api_key = os.environ.get("EMBY_API_KEY")

    if not emby_url or not api_key:
        print("ERROR: EMBY_URL and EMBY_API_KEY environment variables required")
        sys.exit(1)

    # Convert HTTP URL to WebSocket URL
    ws_url = emby_url.replace("https://", "wss://").replace("http://", "ws://")

    # Generate a unique device ID for this test session
    device_id = f"test-ws-{uuid.uuid4().hex[:8]}"

    # Build WebSocket connection URL
    ws_connect_url = f"{ws_url}/embywebsocket?api_key={api_key}&deviceId={device_id}"

    print(f"Connecting to: {ws_url}/embywebsocket")
    print(f"Device ID: {device_id}")
    print("-" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(
                ws_connect_url,
                heartbeat=30,
                ssl=True,
            ) as ws:
                print("Connected successfully!")
                print("-" * 60)

                # Subscribe to session updates (interval in ms)
                subscribe_msg = json.dumps(
                    {
                        "MessageType": "SessionsStart",
                        "Data": "0,1500",  # Initial position, interval in ms
                    }
                )
                await ws.send_str(subscribe_msg)
                print(f"Sent: {subscribe_msg}")
                print("-" * 60)

                # Also try ScheduledTasksInfoStart to see all message types
                scheduled_msg = json.dumps(
                    {"MessageType": "ScheduledTasksInfoStart", "Data": "0,30000"}
                )
                await ws.send_str(scheduled_msg)
                print(f"Sent: {scheduled_msg}")
                print("-" * 60)

                # Activity log subscription
                activity_msg = json.dumps(
                    {"MessageType": "ActivityLogEntryStart", "Data": "0,10000"}
                )
                await ws.send_str(activity_msg)
                print(f"Sent: {activity_msg}")
                print("-" * 60)

                print("\nListening for messages (Ctrl+C to stop)...\n")

                # Track unique message types seen
                seen_types: set[str] = set()

                # Listen for messages
                msg_count = 0
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        msg_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        try:
                            data = json.loads(msg.data)
                            msg_type = data.get("MessageType", "Unknown")
                            msg_data = data.get("Data")

                            # Track new message types
                            if msg_type not in seen_types:
                                seen_types.add(msg_type)
                                print(f"*** NEW MESSAGE TYPE: {msg_type} ***")

                            print(f"[{timestamp}] #{msg_count} MessageType: {msg_type}")

                            if msg_data:
                                if isinstance(msg_data, dict | list):
                                    # Pretty print complex data
                                    formatted = json.dumps(msg_data, indent=2)
                                    # Truncate if too long
                                    if len(formatted) > 2000:
                                        formatted = formatted[:2000] + "\n... (truncated)"
                                    print(f"Data:\n{formatted}")
                                else:
                                    print(f"Data: {msg_data}")

                            print("-" * 60)

                        except json.JSONDecodeError:
                            print(f"[{timestamp}] Raw: {msg.data[:500]}")
                            print("-" * 60)

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        print("Connection closed by server")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"WebSocket error: {ws.exception()}")
                        break

        except aiohttp.ClientError as e:
            print(f"Connection error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\nStopped by user")
