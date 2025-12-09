import json
import logging

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


def send_kafka(topic, data):
    servers = [
        "austx-hadoop-kafka-01.chtrse.com:9092",
        "austx-hadoop-kafka-02.chtrse.com:9092",
        "austx-hadoop-kafka-03.chtrse.com:9092",
    ]
    try:
        producer = KafkaProducer(bootstrap_servers=servers, value_serializer=lambda v: json.dumps(data).encode("utf-8"))
        producer.send(topic, data)
        producer.flush()

    except Exception:
        logger.error("Communication error with Kafka")
