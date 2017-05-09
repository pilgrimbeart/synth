from synth.simulation.solar.solar_math import sun_bright


def check_bright(position, time, expected):
    TO_DP = 3
    assert round(sun_bright(time, position), TO_DP) == round(expected, TO_DP)


def test_sun_bright():
    check_bright((-53.7091967619, 5.835836789), 1111266736, 0.130258764639)
    check_bright((-137.274498513, 62.8175621144), 1156191448, 0.618443681101)
    check_bright((72.5924569508, 33.1801622533), 212847114, 0.149215190953)
    check_bright((-136.116886792, 97.8660069967), 556602493, 0.229300113525)
    check_bright((67.6046592415, 169.725047327), 864906323, 0.0)
    check_bright((-104.056132826, 76.7246032634), 1419644471, 0.0)
    check_bright((-171.511915683, 154.839772438), 265967429, 0.660312220505)
    check_bright((-92.441902747, 89.4234914115), 1539024817, 0.0)
    check_bright((-89.4752325591, 80.1848749333), 1417213110, 0.0)
    check_bright((-157.017530966, 33.3637970585), 500997961, 0.0)
