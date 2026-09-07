from unittest.mock import MagicMock

from simulator.kafka_producer import TOPIC_BY_SENSOR, stream_unit_records


def test_stream_unit_records_sends_to_correct_topics_with_unit_id_key():
    producer = MagicMock()
    records = {
        "temperature": [{"unit_id": "unit_00001", "t": 0.0, "value": 25.0}],
        "vibration": [{"unit_id": "unit_00001", "t": 0.0, "value": 0.8}],
    }

    stream_unit_records(producer, "unit_00001", records)

    calls = producer.send.call_args_list
    assert len(calls) == 2
    sent_topics = {call.args[0] for call in calls}
    assert sent_topics == {"sensor-temperature", "sensor-vibration"}
    for call in calls:
        assert call.kwargs["key"] == "unit_00001"


def test_stream_unit_records_uses_correct_topic_mapping():
    assert TOPIC_BY_SENSOR["current"] == "sensor-current"
    assert TOPIC_BY_SENSOR["torque"] == "sensor-torque"
    assert TOPIC_BY_SENSOR["temperature"] == "sensor-temperature"
    assert TOPIC_BY_SENSOR["vibration"] == "sensor-vibration"


def test_stream_unit_records_forwards_the_full_row_as_value():
    producer = MagicMock()
    records = {"torque": [{"unit_id": "unit_00042", "t": 1.5, "value": 15.2}]}

    stream_unit_records(producer, "unit_00042", records)

    call = producer.send.call_args_list[0]
    assert call.args[0] == "sensor-torque"
    assert call.kwargs["value"] == {"unit_id": "unit_00042", "t": 1.5, "value": 15.2}
