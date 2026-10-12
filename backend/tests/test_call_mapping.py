from api.routes.calls import list_calls
from models.call import Call
from models.enums import CallProvider, CallStatus
from models.sophia_session import SophiaSession


async def test_exact_provider_mapping_and_ambiguous_mapping_denial(db):
    call = Call(provider=CallProvider.signalwire, provider_call_id="synthetic-call", call_status=CallStatus.connected)
    matching = SophiaSession(session_key="synthetic-match", channel_metadata={"call_sid": "synthetic-call"})
    other = SophiaSession(session_key="synthetic-other", channel_metadata={"call_sid": "other-call"})
    db.add_all([call, matching, other])
    await db.flush()
    response = await list_calls(page=1, page_size=50, call_status=None, session=db)
    assert response["items"][0]["sophia_session_id"] == str(matching.id)
    db.add(SophiaSession(session_key="synthetic-ambiguous", channel_metadata={"call_sid": "synthetic-call"}))
    await db.flush()
    response = await list_calls(page=1, page_size=50, call_status=None, session=db)
    assert response["items"][0]["sophia_session_id"] is None


async def test_unmapped_call_never_uses_call_uuid_as_session_uuid(db):
    db.add(Call(provider=CallProvider.signalwire, provider_call_id="synthetic-unmapped", call_status=CallStatus.connected))
    await db.flush()
    response = await list_calls(page=1, page_size=50, call_status=None, session=db)
    assert response["items"][0]["sophia_session_id"] is None
