import time

import pytest
import requests_mock

from synth.clients.old import devicepilot

DEVICEPILOT_URL = "mock://devicepilot.com"


@pytest.fixture
def api():
    dp_api = devicepilot.Api(url=DEVICEPILOT_URL)
    dp_api.set_queue_flush("messages", 1)
    return dp_api


# noinspection PyClassHasNoInit,PyShadowingNames
class TestApi:
    def test_set_queue_flush(self, api):
        assert api.queue_criterion == "messages"
        assert api.queue_limit == 1
        api.set_queue_flush("interactive", 1000)
        assert api.queue_criterion == "interactive"
        assert api.queue_limit == 1000

    def test_post_device(self, api):
        device = {"$id": "upstairs_light", "status": "on"}
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/devices')
            api.post_device(device)
            assert m.request_history[0].method == 'POST'
            assert m.request_history[0].json() == [device]
        devices = [
            {"$id": "upstairs_light", "status": "on"},
            {"$id": "hallway_light", "status": "off"}
        ]
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/devices')
            api.post_device(devices)
            assert m.request_history[0].method == 'POST'
            assert m.request_history[0].json() == devices

    def test_flush_post_queue_if_ready(self, api):
        api.set_queue_flush("messages", 2)
        devices = [
            {"$id": "s7", "state": "exploded"},
            {"$id": "s6", "state": "ok"},
        ]
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/devices')
            api.post_device(devices[0])  # should only post_queue_if_ready!
            assert len(m.request_history) == 0
            api.post_device(devices[1])
            assert m.request_history[0].method == 'POST'
            assert m.request_history[0].json() == devices

    def test_ready_to_flush(self, api):
        # every x messages
        api.post_queue = []
        api.set_queue_flush("messages", 3)
        assert not api.ready_to_flush()
        api.post_queue = [1, 2, 3]
        assert api.ready_to_flush()
        # simulation time passed
        api.post_queue = []
        api.set_queue_flush("time", 3)
        assert not api.ready_to_flush()
        api.post_queue = [{"$ts": 6000}, {"$ts": 8000}]
        assert not api.ready_to_flush()
        api.post_queue.append({"$ts": 13000})
        assert api.ready_to_flush()
        # actual time passed
        api.post_queue = []
        api.set_queue_flush("interactive", time.time())
        assert not api.ready_to_flush()
        api.set_queue_flush("interactive", 0)
        assert api.ready_to_flush()

    def test_recalc_historical(self, api):
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/devices')
            m.put(DEVICEPILOT_URL + '/propertySummaries')
            api.recalc_historical("fake_id")
            assert 'historical' not in m.request_history[0].qs

    def test_enter_interactive(self, api):
        api.enter_interactive()
        assert api.queue_criterion == "interactive"
        assert api.queue_limit == 1

    def test_get_devices(self, api):
        with requests_mock.Mocker() as m:
            m.get(DEVICEPILOT_URL + '/devices', json=[
                {"$id": "buster_sword", "$ts": 123, "$owner": "cloud", "materia": "fire"},
                {"$id": "gatling_gun", "materia": "ice", "watchedState": True}
            ])
            assert api.get_devices() == [
                {"$id": "buster_sword", "$ts": 123, "materia": "fire"},
                {"$id": "gatling_gun", "materia": "ice"}
            ]

    def test_get_devices_where(self, api):
        with requests_mock.Mocker() as m:
            m.get(DEVICEPILOT_URL + "/device_name/history?start=100&end=200&fields=%5B%27hello%27%5D&timezoneOffset=0",
                  json=[])
            api.get_device_history("/device_name", 100, 200, ["hello"])
            assert m.request_history[0]

    def test_delete_all_devices(self, api):
        with requests_mock.Mocker() as m:
            m.delete(DEVICEPILOT_URL + '/devices')
            api.delete_all_devices()
            assert m.request_history[0]

    def test_delete_devices_where(self, api):
        with requests_mock.Mocker() as m:
            m.get(DEVICEPILOT_URL + '/devices?$profile=/profiles/$view', json=[
                {"$urn": "/devices/delete"},
                {"$urn": "/devices/backspace"},
            ])
            m.delete(DEVICEPILOT_URL + "/devices/delete")
            m.delete(DEVICEPILOT_URL + "/devices/backspace")
            where = 'where_clause'
            assert api.delete_devices_where(where)
            assert 'where' in m.request_history[0].qs
            assert m.request_history[1].method == 'DELETE'
            assert m.request_history[2].method == 'DELETE'

    def test_create_filter(self, api):
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/savedSearches', json={"$id": "test_id"})
            assert api.create_filter(name="testing", spec="test_spec") == "test_id"
            body = {"$description": "testing", "where": "test_spec"}
            assert m.request_history[0].json() == body

    def test_create_event_config(self, api):
        with requests_mock.Mocker() as m:
            m.post(DEVICEPILOT_URL + '/incidentConfigs', json={"$id": "test_id"})
            assert api.create_event_config("filter_id", active=False) == "test_id"
            body = {"$savedSearch": "filter_id", "active": False}
            assert m.request_history[0].json() == body
