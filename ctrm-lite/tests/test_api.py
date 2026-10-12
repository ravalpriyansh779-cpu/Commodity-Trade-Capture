"""Integration tests — need a running Postgres loaded with sql/*.sql (see README)."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _trade(**kw):
    d = date.today()
    base = dict(commodity_id=1, counterparty_id=1, side="BUY", quantity="100", price="82",
                delivery_start=str(d + timedelta(days=30)), delivery_end=str(d + timedelta(days=60)))
    return {**base, **kw}


def test_pnl_and_positions(client):
    assert client.get("/pnl").json()["count"] >= 1
    assert client.get("/positions").json()["count"] >= 1


def test_create_amend_cancel_and_audit(client):
    r = client.post("/trades", json=_trade(), headers={"X-User": "alice"})
    assert r.status_code == 201
    tid = r.json()["trade_id"]
    assert client.patch(f"/trades/{tid}", json={"price": "83"}, headers={"X-User": "bob"}).status_code == 200
    assert client.post(f"/trades/{tid}/cancel", headers={"X-User": "bob"}).json()["status"] == "CANCELLED"
    rows = client.get("/audit", params={"trade_id": tid}).json()
    assert [r["action"] for r in rows][::-1] == ["INSERT", "UPDATE", "UPDATE"]
    assert rows[-1]["changed_by"] == "alice"


def test_validators(client):
    assert client.post("/trades", json=_trade(price="200")).status_code == 422          # fat finger
    assert client.post("/trades", json=_trade(quantity="99999999")).status_code == 422  # credit limit
    assert client.post("/trades", json=_trade(counterparty_id=999)).status_code == 422
    assert client.get("/trades/999999").status_code == 404
