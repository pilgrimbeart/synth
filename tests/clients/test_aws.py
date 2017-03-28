import pytest
import json

from synth.clients import aws

DEMO_THINGS = [
    {"thingTypeName": aws.DEFAULT_TYPENAME, "thingName": "highwind"},
    {"thingTypeName": aws.DEFAULT_TYPENAME, "thingName": "ragnarok"},
    {"thingTypeName": "plane", "thingName": "tinybronco"}
]


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload


# mock to match boto3, therefore:
# noinspection PyPep8Naming
class Mockiot_client:
    def __init__(self, _):
        self.posted = None
        self.things = []
        pass

    # Stubs
    @staticmethod
    def create_thing_type(thingTypeName, thingTypeProperties):
        return {"thingTypeArn": thingTypeName + '/' + thingTypeProperties["thingTypeDescription"]}

    @staticmethod
    def create_thing(thingName, thingTypeName):
        return {"thingArn": thingTypeName + '/' + thingName}

    @staticmethod
    def get_thing_shadow(thingName):
        return {"payload": MockResponse({"$id": thingName})}

    @staticmethod
    def list_things():
        return {"things": DEMO_THINGS}

    def update_thing_shadow(self, thingName, payload):
        self.posted = {"name": thingName, "payload": payload}
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def delete_thing_shadow(self, thingName):
        response = 404
        if thingName in self.things:
            response = 200
            self.things.remove(thingName)
        return {"ResponseMetadata": {"HTTPStatusCode": response}}

    def delete_thing(self, thingName):
        response = 404
        if thingName in self.things:
            response = 200
            self.things.remove(thingName)
        return {"ResponseMetadata": {"HTTPStatusCode": response}}

    # Accessors
    def last_posted(self):
        return self.posted

    def add_thing(self, name):
        self.things.append(name)

    def has_thing(self, name):
        return name in self.things


@pytest.fixture
def api(mocker):
    mocker.patch.object(aws, 'boto3')
    aws.boto3.client = Mockiot_client
    aws_api = aws.Api()
    return aws_api


# noinspection PyClassHasNoInit,PyShadowingNames
class TestApi:
    def test_create_device_type(self, api):
        assert api.create_device_type().startswith(aws.DEFAULT_TYPENAME)
        assert api.create_device_type(type_name="light", description="a smart light") == "light/a smart light"

    def test_create_device(self, api):
        assert api.create_device("house_light") == aws.DEFAULT_TYPENAME + '/' + "house_light"
        assert api.create_device("toy_car", type_name="toy") == "toy/toy_car"

    def test_get_device(self, api):
        assert api.get_device("dave's_bulb") == {"$id": "dave's_bulb"}

    def test_get_devices(self, api):
        assert api.get_devices() == DEMO_THINGS

    def test_post_device(self, api):
        state = {"$id": "bob's_car", "speed": "50mph"}
        api.post_device(state)
        assert api.iot_data.last_posted() == {
            "name": "bob's_car",
            "payload": json.dumps({"state": {"reported": state}})
        }

    def test_post(self, api):
        payload = {"arm": "lifted"}
        api.post("bob's_digger", payload)
        assert api.iot_data.last_posted() == {
            "name": "bob's_digger",
            "payload": json.dumps({"state": {"reported": payload}})
        }

    def test_delete_device(self, api):
        # With shadow
        api.iot_client.add_thing("dave's_tractor")
        api.iot_data.add_thing("dave's_tractor")
        assert api.iot_data.has_thing("dave's_tractor")
        assert api.delete_device("dave's_tractor")
        assert not api.iot_data.has_thing("dave's_tractor")
        # Without shadow
        api.iot_client.add_thing("dave's_castle")
        assert api.delete_device("dave's_castle")
        # Without anything
        assert not api.delete_device("dave's_airship")

    def test_delete_default_devices(self, api):
        api.iot_client.add_thing("highwind")
        api.iot_client.add_thing("ragnarok")
        api.iot_client.add_thing("tiny_bronco")
        api.delete_default_devices()
        assert not api.iot_client.has_thing("highwind")
        assert not api.iot_client.has_thing("ragnarok")
        assert api.iot_client.has_thing("tiny_bronco")
