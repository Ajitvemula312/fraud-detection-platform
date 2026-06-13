from __future__ import annotations

import json
from typing import Any


class KafkaTransactionProducer:
    def __init__(self, bootstrap_servers: str, topic: str):
        try:
            from kafka import KafkaProducer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "kafka-python is not installed. Install optional streaming dependencies with "
                "`pip install -e \".[streaming]\"`."
            ) from exc
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
        )

    def publish(self, payload: dict[str, Any]) -> None:
        self.producer.send(self.topic, payload)
        self.producer.flush()

