import requests_mock

from synth.simulation.geo.google_maps import address_to_long_lat


def test_address_to_long_lat():
    with requests_mock.Mocker() as m:
        m.get('https://maps.googleapis.com/maps/api/geocode/json', json={
            'results': [
                {'geometry': {'location': {'lng': 123.456, 'lat': 3.21}}}
            ]})
        assert address_to_long_lat('my_house') == (123.456, 3.21)
        assert 'my_house' in m.request_history[0].url
