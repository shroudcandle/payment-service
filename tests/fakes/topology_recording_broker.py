from __future__ import annotations

from typing import Any

from tests.fakes.topology_recording_queue import TopologyRecordingQueue


class TopologyRecordingBroker:
    def __init__(self) -> None:
        self.exchanges: list[str] = []
        self.queues: list[TopologyRecordingQueue] = []

    async def declare_exchange(self, exchange: Any) -> Any:
        self.exchanges.append(exchange.name)
        return exchange

    async def declare_queue(self, queue: Any) -> TopologyRecordingQueue:
        recording_queue = TopologyRecordingQueue(queue.name)
        self.queues.append(recording_queue)
        return recording_queue
