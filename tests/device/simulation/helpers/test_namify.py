from synth.device.simulation.helpers.namify import first_name, last_name


def verify_consistent_naming(namer):
    seed_one = 123
    name_one = namer(seed_one)
    assert name_one == namer(seed_one)
    seed_two = 456
    name_two = namer(seed_two)
    assert name_one != name_two


def test_first_name():
    verify_consistent_naming(first_name)


def test_last_name():
    verify_consistent_naming(last_name)
