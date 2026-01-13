import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine, SessionLocal
from app.main import app


def waitForDatabaseReady(timeoutSeconds: int = 30) -> None:
    """目的: テスト開始前にDB接続が可能になるまで待機し、起動レースを避ける。"""
    startTime = time.time()
    lastError: Exception | None = None

    while time.time() - startTime < timeoutSeconds:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as e:
            lastError = e
            time.sleep(0.5)

    raise RuntimeError(f"Database was not ready within {timeoutSeconds}s: {lastError}")


@pytest.fixture(scope="session", autouse=True)
def ensureDatabaseReady() -> None:
    """目的: テスト全体の開始時に、DBが利用可能になるまで待機する。"""
    waitForDatabaseReady()


@pytest.fixture()
def client() -> TestClient:
    """目的: FastAPIのTestClientを提供し、startup/shutdownイベントを確実に実行する。"""
    with TestClient(app) as testClient:
        yield testClient


@pytest.fixture()
def db():
    """目的: テスト内で直接DBをクエリできるようにSessionLocalを提供する。"""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture(autouse=True)
def forceTestEnvDefaults(monkeypatch):
    """
    目的: テストがローカルの .env / compose の環境変数に影響されないようにする。
    - 既定では LLM を使わずテンプレ分析にする（ANALYSIS_USE_LLM=0）
    - LLM関連の個別テストは monkeypatch.setenv(...) で上書きできる
    """
    monkeypatch.setenv("ANALYSIS_USE_LLM", "0")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    # APIキーが入っていてもテストからは参照しない前提だが、念のため空にしておく
    monkeypatch.setenv("LLM_API_KEY", "")
    yield


@pytest.fixture(autouse=True)
def cleanDatabase() -> None:
    """目的: 各テストが独立して再現できるよう、テストごとにDBをクリーンにする。"""
    yield

    with engine.begin() as connection:
        # dataset_rows -> datasets の順に消す必要があるが、CASCADEで依存も含めて掃除する
        connection.execute(text("TRUNCATE TABLE dataset_rows, datasets RESTART IDENTITY CASCADE"))

