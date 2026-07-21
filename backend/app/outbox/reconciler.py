"""Reconciler: promove pending/enqueue_failed para a fila RQ `default`."""

from __future__ import annotations

import os
import time

from app.outbox.db_store import SqlAlchemyOutboxStore
from app.outbox.rq_client import RqJobEnqueuer
from app.outbox.service import (
    ELIGIBLE_STATUSES,
    OutboxDispatcher,
    OutboxRecord,
    OutboxStore,
)


class OutboxReconciler:
    def __init__(self, dispatcher: OutboxDispatcher, store: OutboxStore) -> None:
        self._dispatcher = dispatcher
        self._store = store

    def reconcile(self) -> list[OutboxRecord]:
        results: list[OutboxRecord] = []
        for job in self._store.list_by_statuses(ELIGIBLE_STATUSES):
            results.append(self._dispatcher.try_enqueue(job.id))
        return results


def _interval_seconds() -> float:
    return float(os.getenv("OUTBOX_RECONCILE_INTERVAL_SECONDS", "5"))


def main() -> None:
    store = SqlAlchemyOutboxStore()
    dispatcher = OutboxDispatcher(store=store, enqueuer=RqJobEnqueuer())
    reconciler = OutboxReconciler(dispatcher=dispatcher, store=store)
    interval = _interval_seconds()
    while True:
        reconciler.reconcile()
        time.sleep(interval)


if __name__ == "__main__":
    main()
