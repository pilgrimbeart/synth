from synth.device.simulation.helpers.utilities import consistent_hash


def test_consistent_hash():
    seed_one = 123
    hash_one = consistent_hash(seed_one, 1000)
    assert hash_one == consistent_hash(seed_one, 1000)
    seed_two = 456
    hash_two = consistent_hash(seed_two, 1000)
    assert hash_one != hash_two
    assert consistent_hash(123, 1) <= 1
