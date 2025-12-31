def testGetHealthReturnsOk(client):
    """目的: /health が稼働確認用に 200 と status=ok を返すことを確認する。"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


