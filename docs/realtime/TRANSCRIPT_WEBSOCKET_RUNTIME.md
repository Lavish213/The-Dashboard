# Transcript WebSocket Runtime

## Purpose

Realtime deterministic transcript streaming.

Infrastructure layer only.

---

## Allowed Event Types

- transcript.created
- transcript.started
- transcript.chunk_added
- transcript.paused
- transcript.resumed
- transcript.completed
- transcript.failed
- transcript.archived

---

## Event Rules

All websocket events must be:

- typed
- versioned
- ordered
- replay-safe

Required fields:

- event_id
- transcript_id
- event_type
- timestamp
- sequence

---

## Streaming Rules

- stream chunks only
- never send entire transcript repeatedly
- incremental append model only
- reconnect resumes from sequence checkpoint

---

## Replay Rules

Replay ordering:

1. sequence
2. timestamp
3. id

Replay must produce identical transcript state.

---

## Transport Rules

- compact payloads
- no giant websocket frames
- pagination for historical fetches
- no hidden background enrichment

---

## Forbidden

- AI summarization
- embeddings
- autonomous actions
- memory injection
- hidden inference layers