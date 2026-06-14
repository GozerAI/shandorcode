"""Phase 1.4 tests for the multi-repo WebSocket envelope + subscriptions."""
import json
from pathlib import Path

from fastapi.testclient import TestClient


def _send_action(ws, action: str, repo_ids: list[str]) -> None:
    ws.send_text(json.dumps({"action": action, "repo_ids": repo_ids}))


def test_envelope_shape_on_legacy_analyze(analyzed_client: TestClient) -> None:
    with analyzed_client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        while msg["type"] == "hello":
            msg = ws.receive_json()
        assert {"type", "repo_id", "payload"} <= msg.keys()
        assert msg["type"] == "graph"
        assert msg["repo_id"]
        assert "entities" in msg["payload"]


def test_hello_envelope_per_registered_repo(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        assert first["type"] == "hello"
        assert first["repo_id"] == "demo"
        assert first["payload"]["status"] == "not_analyzed"


def test_subscribe_unsubscribe_round_trip(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        _send_action(ws, "subscribe", ["alpha", "beta"])
        ack = ws.receive_json()
        assert ack["type"] == "subscribed"
        assert set(ack["payload"]["repo_ids"]) >= {"alpha", "beta"}

        _send_action(ws, "unsubscribe", ["alpha", "*"])
        ack2 = ws.receive_json()
        assert "alpha" not in ack2["payload"]["repo_ids"]
        assert "*" not in ack2["payload"]["repo_ids"]


def test_refresh_emits_graph_only_to_subscribed(
    client: TestClient, tmp_path: Path
) -> None:
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    for repo in (repo_a, repo_b):
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("def f(): pass\n", encoding="utf-8")
    client.post("/api/repos", json={"slug": "a", "path": str(repo_a)})
    client.post("/api/repos", json={"slug": "b", "path": str(repo_b)})

    with client.websocket_connect("/ws") as ws:
        for _ in range(2):
            ws.receive_json()  # drain hello envelopes

        _send_action(ws, "unsubscribe", ["*"])
        ws.receive_json()  # drain subscribed ack
        _send_action(ws, "subscribe", ["a"])
        ws.receive_json()

        client.post("/api/repos/b/refresh")  # should NOT reach this client
        client.post("/api/repos/a/refresh")  # should reach
        msg = ws.receive_json()
        assert msg["type"] == "graph"
        assert msg["repo_id"] == "a"
