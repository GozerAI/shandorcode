"""WebSocket /ws endpoint behavior.

Pins the single-channel broadcast model that Phase 1.4 will replace with a
per-repo envelope.
"""
from pathlib import Path

from fastapi.testclient import TestClient


def test_ws_accepts_connection_when_no_graph(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_ws_emits_graph_on_connect_after_analyze(
    analyzed_client: TestClient,
) -> None:
    with analyzed_client.websocket_connect("/ws") as ws:
        # Phase 1.4 added per-repo `hello` envelopes that fire before the
        # legacy graph dump. Drain them, then expect the graph event.
        msg = ws.receive_json()
        while msg["type"] == "hello":
            msg = ws.receive_json()
        assert msg["type"] == "graph"
        assert "entities" in msg["payload"]


def test_ws_ping_pong_keepalive(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        for _ in range(3):
            ws.send_text("ping")
            assert ws.receive_text() == "pong"
