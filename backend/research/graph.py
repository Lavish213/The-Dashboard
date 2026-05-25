"""
ResearchTaskGraph — DAG primitives for research task dependency management.

Provides:
- build()           — create tasks + dependency edges from a GraphSpec
- validate()        — detect cycles before execution
- topological_order() — deterministic BFS-based topological sort
- is_unblocked()    — check whether all upstreams of a task are complete

No side effects on validation — read-only analysis of graph structure.
Raises ResearchCycleError on cycle detection.
Raises ResearchGraphError on structural problems.
"""
from __future__ import annotations

from collections import defaultdict, deque
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType, ResearchTaskStatus
from models.research_task import ResearchTask
from repositories.research_event import ResearchEventRepository
from repositories.research_task import ResearchTaskRepository
from research.contracts import (
    ResearchGraphOrder,
    ResearchGraphSpec,
    ResearchTaskRecord,
)


class ResearchGraphError(Exception):
    pass


class ResearchCycleError(ResearchGraphError):
    pass


class ResearchTaskGraph:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = ResearchTaskRepository(session)
        self._events = ResearchEventRepository(session)

    async def build(self, spec: ResearchGraphSpec) -> list[ResearchTaskRecord]:
        """
        Persist all tasks and dependency edges from a GraphSpec.
        Validates for cycles before writing dependencies.
        Returns task records in task_index order.
        """
        # Validate graph structure before writing anything
        self._validate_spec(spec)

        # Persist tasks
        records: list[ResearchTaskRecord] = []
        index_to_id: dict[int, UUID] = {}

        for task_spec in spec.tasks:
            # Idempotent on task_key
            if task_spec.task_key:
                existing = await self._tasks.get_by_key(task_spec.task_key)
                if existing:
                    records.append(self._to_record(existing))
                    index_to_id[task_spec.task_index] = existing.id
                    continue

            row = ResearchTask(
                job_id=task_spec.job_id,
                task_index=task_spec.task_index,
                task_type=task_spec.task_type,
                input_payload=task_spec.input_payload,
                depth=task_spec.depth,
                max_retries=task_spec.max_retries,
                task_key=task_spec.task_key,
            )
            self._session.add(row)
            await self._session.flush()

            await self._events.append(
                ResearchEventType.task_created,
                job_id=task_spec.job_id,
                task_id=row.id,
                payload={"task_index": task_spec.task_index, "task_type": task_spec.task_type},
            )
            records.append(self._to_record(row))
            index_to_id[task_spec.task_index] = row.id

        # Persist dependency edges
        for dep_spec in spec.dependencies:
            await self._tasks.add_dependency(
                job_id=dep_spec.job_id,
                upstream_task_id=dep_spec.upstream_task_id,
                downstream_task_id=dep_spec.downstream_task_id,
            )

        return sorted(records, key=lambda r: r.task_index)

    async def topological_order(self, job_id: UUID) -> ResearchGraphOrder:
        """
        Kahn's algorithm — deterministic topological sort.
        Returns task indices in execution order, grouped into parallel levels.
        Raises ResearchCycleError if a cycle is detected.
        """
        tasks = await self._tasks.list_by_job(job_id)
        deps = await self._tasks.get_dependencies(job_id)

        # Map task_id → task_index for output
        id_to_index = {t.id: t.task_index for t in tasks}

        # Build adjacency: upstream_id → set of downstream_ids
        adjacency: dict[UUID, set[UUID]] = defaultdict(set)
        in_degree: dict[UUID, int] = {t.id: 0 for t in tasks}

        for dep in deps:
            adjacency[dep.upstream_task_id].add(dep.downstream_task_id)
            in_degree[dep.downstream_task_id] = in_degree.get(dep.downstream_task_id, 0) + 1

        # BFS-based Kahn's — process nodes with in_degree == 0
        queue: deque[UUID] = deque(
            sorted(
                (tid for tid, deg in in_degree.items() if deg == 0),
                key=lambda tid: id_to_index[tid],  # deterministic order
            )
        )
        ordered_indices: list[int] = []
        levels: list[tuple[int, ...]] = []
        visited = 0

        while queue:
            # Collect all nodes at current level (same in_degree frontier)
            level_size = len(queue)
            level_indices: list[int] = []

            for _ in range(level_size):
                node = queue.popleft()
                ordered_indices.append(id_to_index[node])
                level_indices.append(id_to_index[node])
                visited += 1

                for downstream in sorted(
                    adjacency[node],
                    key=lambda tid: id_to_index[tid],
                ):
                    in_degree[downstream] -= 1
                    if in_degree[downstream] == 0:
                        queue.append(downstream)

            levels.append(tuple(sorted(level_indices)))

        if visited != len(tasks):
            raise ResearchCycleError(
                f"Cycle detected in task graph for job {job_id}"
            )

        return ResearchGraphOrder(
            job_id=job_id,
            task_indices=tuple(ordered_indices),
            levels=tuple(levels),
        )

    async def is_unblocked(self, task_id: UUID) -> bool:
        """
        Returns True if all upstream tasks are completed.
        A task with no upstreams is always unblocked.
        """
        upstreams = await self._tasks.get_upstreams(task_id)
        if not upstreams:
            return True

        for edge in upstreams:
            upstream = await self._tasks.get(edge.upstream_task_id)
            if upstream is None or upstream.status != ResearchTaskStatus.completed:
                return False
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_spec(self, spec: ResearchGraphSpec) -> None:
        """In-memory cycle check on the spec before DB writes."""
        indices = {t.task_index for t in spec.tasks}
        if len(indices) != len(spec.tasks):
            raise ResearchGraphError("Duplicate task_index values in GraphSpec")

        # Kahn's on the UUID-based graph
        adj_uuid: dict[UUID, set[UUID]] = defaultdict(set)
        in_deg_uuid: dict[UUID, int] = {}

        # Collect all UUIDs from dependencies
        all_uuids: set[UUID] = set()
        for dep in spec.dependencies:
            all_uuids.add(dep.upstream_task_id)
            all_uuids.add(dep.downstream_task_id)
            adj_uuid[dep.upstream_task_id].add(dep.downstream_task_id)
            in_deg_uuid[dep.downstream_task_id] = in_deg_uuid.get(dep.downstream_task_id, 0) + 1

        for uid in all_uuids:
            if uid not in in_deg_uuid:
                in_deg_uuid[uid] = 0

        queue: deque[UUID] = deque(uid for uid, d in in_deg_uuid.items() if d == 0)
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for downstream in adj_uuid[node]:
                in_deg_uuid[downstream] -= 1
                if in_deg_uuid[downstream] == 0:
                    queue.append(downstream)

        if visited < len(all_uuids):
            raise ResearchCycleError("Cycle detected in GraphSpec dependency edges")

    def _to_record(self, row: ResearchTask) -> ResearchTaskRecord:
        from research.contracts import ResearchTaskRecord  # noqa: PLC0415
        return ResearchTaskRecord(
            task_id=row.id,
            job_id=row.job_id,
            task_index=row.task_index,
            task_type=row.task_type,
            status=row.status,
            input_payload=row.input_payload,
            depth=row.depth,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            tokens_input=row.tokens_input,
            tokens_output=row.tokens_output,
            created_at=row.created_at,
            task_key=row.task_key,
            output_payload=row.output_payload,
            error=row.error,
            governance_verdict=row.governance_verdict,
            approval_id=row.approval_id,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
