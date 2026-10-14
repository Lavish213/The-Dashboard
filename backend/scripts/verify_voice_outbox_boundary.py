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
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from models.call import Call
from models.lead import Lead
from models.registry import load_all_models
from models.sophia_session import SophiaSession
from models.sophia_turn import SophiaTurn
from models.transcript import Transcript
from models.transcript_chunk import TranscriptChunk
from testing.database import validate_disposable_database

SERVER = '''
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.routes import ingest, sophia_bridge
from models.registry import load_all_models
load_all_models()
application = FastAPI()
application.include_router(ingest.router, prefix="/api/v1/ingest")
application.include_router(sophia_bridge.router, prefix="/api/v1/sophia")
@application.get("/healthz")
async def health():
    return {"status": "ok"}
class FaultReceiver:
    def __init__(self):
        self.before = 0
        self.after = 0
    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] == "http" and path.endswith("/ingest/call") and self.before < 2:
            self.before += 1
            await JSONResponse({"detail": "synthetic outage before persistence"}, status_code=503)(scope, receive, send)
            return
        if scope["type"] == "http" and path.endswith("/ingest/transcript") and self.after < 2:
            self.after += 1
            response = JSONResponse({"detail": "synthetic acknowledgement lost after commit"}, status_code=503)
            async def lost_ack(message):
                if message["type"] == "http.response.start" and message["status"] == 200:
                    await send({"type": "http.response.start", "status": 503, "headers": response.raw_headers})
                elif message["type"] == "http.response.body":
                    await send({"type": "http.response.body", "body": response.body})
                else:
                    await send(message)
            await application(scope, receive, lost_ack)
            return
        await application(scope, receive, send)
app = FaultReceiver()
'''


async def counts(database_url, sid, external):
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine) as session:
            call = await session.scalar(select(Call).where(Call.provider_call_id == sid))
            if call is None:
                return {"calls": 0, "turns": 0, "transcripts": 0, "chunks": 0}
            lead = await session.get(Lead, call.lead_id)
            assert str(lead.id) != external
            sessions = select(SophiaSession.id).where(SophiaSession.channel_metadata["call_sid"].as_string() == sid)
            transcripts = select(Transcript.id).where(Transcript.call_id == call.id)
            return {"calls": await session.scalar(select(func.count()).select_from(Call).where(Call.provider_call_id == sid)), "turns": await session.scalar(select(func.count()).select_from(SophiaTurn).where(SophiaTurn.session_id.in_(sessions))), "transcripts": await session.scalar(select(func.count()).select_from(Transcript).where(Transcript.call_id == call.id)), "chunks": await session.scalar(select(func.count()).select_from(TranscriptChunk).where(TranscriptChunk.transcript_id.in_(transcripts)))}
    finally:
        await engine.dispose()


async def cleanup(database_url, sid, external):
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            call_ids = select(Call.id).where(Call.provider_call_id == sid)
            transcript_ids = select(Transcript.id).where(Transcript.call_id.in_(call_ids))
            session_ids = select(SophiaSession.id).where(SophiaSession.channel_metadata["call_sid"].as_string() == sid)
            await connection.execute(delete(TranscriptChunk).where(TranscriptChunk.transcript_id.in_(transcript_ids)))
            await connection.execute(delete(Transcript).where(Transcript.call_id.in_(call_ids)))
            await connection.execute(delete(SophiaTurn).where(SophiaTurn.session_id.in_(session_ids)))
            await connection.execute(delete(SophiaSession).where(SophiaSession.channel_metadata["call_sid"].as_string() == sid))
            await connection.execute(delete(Call).where(Call.provider_call_id == sid))
            await connection.execute(delete(Lead).where(Lead.metadata_["external_lead_id"].as_string() == external))
    finally:
        await engine.dispose()


def main():
    database_url = os.environ["TEST_DATABASE_URL"]
    validate_disposable_database(database_url)
    if os.environ["DATABASE_URL"] != database_url:
        raise RuntimeError("Boundary verification requires the same disposable database")
    source = Path(os.environ["REI_REPO"])
    producer_python = os.environ["REI_CONTRACT_PYTHON"]
    load_all_models()
    sid, external = "outbox-contract-" + str(uuid4()), str(uuid4())
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "boundary_app.py").write_text(SERVER)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server_environment = {**os.environ, "PYTHONPATH": str(Path.cwd()), "KARPATHYS_WEBHOOK_SECRET": "synthetic-boundary-secret"}
        with (root / "receiver.log").open("w") as log:
            receiver = subprocess.Popen([sys.executable, "-m", "uvicorn", "boundary_app:app", "--app-dir", directory, "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"], env=server_environment, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 20
                while True:
                    if receiver.poll() is not None:
                        raise RuntimeError("Synthetic receiver failed: " + (root / "receiver.log").read_text()[-2000:])
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Synthetic receiver startup timed out")
                        time.sleep(0.1)
                environment = {**os.environ, "PYTHONPATH": str(source), "KARPATHYS_URL": f"http://127.0.0.1:{port}", "KARPATHYS_WEBHOOK_SECRET": "synthetic-boundary-secret", "KARPATHYS_OUTBOX_PATH": str(root / "journal.sqlite3"), "CONTRACT_CALL_SID": sid, "CONTRACT_LEAD_ID": external, "BOB_REPO": os.environ["BOB_REPO"]}
                evidence = []
                for number, phase in enumerate(("stage", "resume", "resume")):
                    result_path = root / f"result-{number}.json"
                    result = subprocess.run([producer_python, str(source / "tests/dashboard_bridge_process.py"), phase, str(result_path)], cwd=source, env=environment, capture_output=True, text=True, timeout=45)
                    if result.returncode:
                        raise RuntimeError("Synthetic producer failed: " + result.stderr[-2000:])
                    data = json.loads(result_path.read_text())
                    data["persisted"] = asyncio.run(counts(database_url, sid, external))
                    evidence.append(data)
                    if number < 2:
                        time.sleep(2.1)
                assert evidence[0]["health"]["pending"] == 5 and evidence[0]["persisted"]["calls"] == 0
                assert evidence[1]["health"]["pending"] == 3 and evidence[1]["persisted"]["chunks"] == 2
                assert evidence[2]["health"]["pending"] == 0 and evidence[2]["health"]["delivered"] == 5
                assert evidence[2]["persisted"] == {"calls": 1, "turns": 1, "transcripts": 1, "chunks": 2}
                business_result = root / "business-result.json"
                result = subprocess.run([producer_python, str(source / "tests/dashboard_bridge_process.py"), "business", str(business_result)], cwd=source, env=environment, capture_output=True, text=True, timeout=45)
                if result.returncode:
                    raise RuntimeError("Business producer failed: " + result.stderr[-2000:])
                async def business_record():
                    engine = create_async_engine(database_url)
                    try:
                        async with AsyncSession(engine) as session:
                            lead = await session.scalar(select(Lead).where(Lead.metadata_["external_lead_id"].as_string() == external))
                            return lead.metadata_["business_evidence"]["snapshot"]
                    finally:
                        await engine.dispose()
                snapshot = asyncio.run(business_record())
                assert snapshot["valuation"]["point_cents"] == 46000000
                assert len(snapshot["comparables"]) == 3
                assert snapshot["offers"][0]["amount_cents"] == 25000000
                assert snapshot["appointment"]["status"] == "confirmed"
                assert snapshot["offer_authorized"] is False
                report = {"status": "passed", "fixture_only": True, "process_restarts": 2, "checks": ["real HTTP authentication and PostgreSQL persistence", "turn staged before root waits for call creation", "outage before persistence survives producer restart", "lost acknowledgement after committed transcript survives restart", "replay persists one call, one transcript and exactly two chunks", "actual Bob pricing and REI business snapshot persist exact cents, three comps, draft offer and appointment without authority"], "phases": evidence}
                Path("voice-outbox-boundary-results.json").write_text(json.dumps(report, indent=2) + "\n")
                sys.stdout.write("Voice outbox boundary passed: real HTTP, PostgreSQL, two producer restarts, pre-write outage and post-commit acknowledgement loss\n")
            finally:
                receiver.terminate()
                try:
                    receiver.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    receiver.kill()
                    receiver.wait(timeout=5)
                asyncio.run(cleanup(database_url, sid, external))


if __name__ == "__main__":
    main()
