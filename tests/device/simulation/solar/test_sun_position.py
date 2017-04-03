from synth.device.simulation.solar.sun_position import sun_position


def check_position(got, expected):
    TO_DP = 1
    got_azimuth, got_elevation = got
    expected_azimuth, expected_elevation = expected
    assert round(got_azimuth, TO_DP) == round(expected_azimuth, TO_DP)
    assert round(got_elevation, TO_DP) == round(expected_elevation, TO_DP)
    return True


def test_sun_position():
    # tests defined in original implementation.
    assert check_position(sun_position(2014, 7, 1, latitude=0, longitude=0), (2.26, 66.89))
    assert check_position(sun_position(2012, 12, 22, latitude=41, longitude=0), (180.30, 25.6))
    assert check_position(sun_position(2012, 12, 22, latitude=-41, longitude=0), (359.08, 72.43))
