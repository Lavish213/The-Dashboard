import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.routes.source_review import source_request
from services.connection_status import connection_status
from testing.database import validate_disposable_database

RECEIVER = """
from fastapi import FastAPI
from api.routes.ingest import router
app=FastAPI()
app.include_router(router,prefix='/api/v1/ingest')
@app.get('/healthz')
async def health():
    return {'status':'ok'}
"""

SOURCE = """
from datetime import UTC,datetime
from fastapi import FastAPI
from backend.api.routes.bob import router
from backend.api.security import OperatorAuthentication
from backend.lib import db
db.bob_integration_health=lambda:{'worker':{'completed_at':datetime.now(UTC).isoformat(),'errors':0}}
db.bob_fact_journal_health=lambda:{'dead':0,'oldest_pending_seconds':0}
db.dashboard_event_journal_health=lambda:{'dead':0,'oldest_pending_seconds':0}
app=FastAPI()
app.add_middleware(OperatorAuthentication)
app.include_router(router,prefix='/api')
"""


def port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_ready(process, endpoint):
    deadline = time.monotonic() + 20
    while process.poll() is None:
        try:
            with urlopen(endpoint, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            if time.monotonic() >= deadline:
                break
            time.sleep(0.1)
    raise RuntimeError("Disposable connection service failed to start")


async def inspect(database):
    engine = create_async_engine(database)
    try:
        async with AsyncSession(engine) as session:
            good = await connection_status(session, source_request)
            assert good["status"] == "ok", good
            assert good["outbound_enabled"] is good["background_jobs_enabled"] is False
            retained = os.environ["SOURCE_COMMAND_SECRET"]
            try:
                os.environ["SOURCE_COMMAND_SECRET"] = "wrong-secret-" * 4
                denied = await connection_status(session, source_request)
                assert denied["status"] == "degraded"
                assert (
                    next(
                        row
                        for row in denied["components"]
                        if row["id"] == "dashboard_to_sophia"
                    )["status"]
                    == "unconfirmed"
                )
            finally:
                os.environ["SOURCE_COMMAND_SECRET"] = retained
            return good
    finally:
        await engine.dispose()


def main():
    database = os.environ["TEST_DATABASE_URL"]
    validate_disposable_database(database)
    if os.environ["DATABASE_URL"] != database:
        raise RuntimeError("Connection checks require the same disposable database")
    source = Path(os.environ["REI_REPO"])
    source_python = os.environ["REI_CONTRACT_PYTHON"]
    receiver_port, source_port = port(), port()
    while source_port == receiver_port:
        source_port = port()
    tenant = "00000000-0000-0000-0000-000000000001"
    secret = "synthetic-connection-command-" * 2
    environment = {
        **os.environ,
        "KARPATHYS_URL": f"http://127.0.0.1:{receiver_port}",
        "KARPATHYS_WEBHOOK_SECRET": "synthetic-connection-events-" * 2,
        "SOURCE_COMMAND_SECRET": secret,
        "TENANT_ID": tenant,
        "REI_SOURCE_TENANT_ID": tenant,
        "OUTBOUND_ENABLED": "false",
        "ENABLE_BACKGROUND_JOBS": "false",
    }
    processes = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "wire_receiver.py").write_text(RECEIVER)
        (root / "wire_source.py").write_text(SOURCE)
        with (root / "services.log").open("w") as log:
            try:
                for name, interpreter, module_path, listen_port in [
                    ("wire_receiver", sys.executable, str(Path.cwd()), receiver_port),
                    ("wire_source", source_python, str(source), source_port),
                ]:
                    process = subprocess.Popen(
                        [
                            interpreter,
                            "-m",
                            "uvicorn",
                            name + ":app",
                            "--app-dir",
                            directory,
                            "--host",
                            "127.0.0.1",
                            "--port",
                            str(listen_port),
                            "--log-level",
                            "warning",
                        ],
                        env={**environment, "PYTHONPATH": module_path},
                        cwd=module_path,
                        stdout=log,
                        stderr=log,
                    )
                    processes.append(process)
                    wait_ready(process, f"http://127.0.0.1:{listen_port}/healthz")
                assert (
                    httpx.get(
                        f"http://127.0.0.1:{receiver_port}/api/v1/ingest/connection?challenge=00000000-0000-0000-0000-000000000001"
                    ).status_code
                    == 401
                )
                os.environ["REI_COMMAND_URL"] = f"http://127.0.0.1:{source_port}"
                os.environ["SOURCE_COMMAND_SECRET"] = secret
                report = asyncio.run(inspect(database))
                report.update(
                    fixture_only=True,
                    bob_health_is_fixture=True,
                    scope="actual_dashboard_database_and_authenticated_http_both_directions_not_a_live_provider_or_Bob_worker_test",
                )
                Path("project-connection-boundary-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
                sys.stdout.write(
                    "Project connections passed: actual PostgreSQL plus authenticated HTTP in both directions; wrong command secret denied; Bob health is explicitly a fixture\n"
                )
            finally:
                for process in processes:
                    process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
