from synth.simulation.geo.point_picker import PointPicker


# noinspection PyClassHasNoInit
class TestPointPicker:
    def test_set_area(self):
        pp = PointPicker(random_seed=1)
        assert not pp.restrict_to_area
        pp.set_area((51.5007, 0.1246), (51.5055, 0.0754))
        assert pp.restrict_to_area
        assert pp.area_centre_xy == pp.lon_lat_to_xy((51.5007, 0.1246))
        assert str(pp.area_radius_pixels)[:4] == "1.85"  # truncate to avoid floating math.

    def test_pick_points(self):
        pp = PointPicker(random_seed=1)
        points = pp.pick_points(2)
        assert len(points) == 2
        assert points[0] != points[1]

    def test_pick_point(self):
        pp = PointPicker(random_seed=1)
        pp.set_area((51.5007, 0.1246), (51.5055, 0.0754))
        (lon, lat) = pp.pick_point()
        dither = 1.0
        assert 51.5007 < lon
        assert lon < (51.5055 + dither)
        assert 0.0754 < lat
        assert lat < (0.1246 + dither)

    def test_lon_lat_to_xy(self):
        pp = PointPicker(random_seed=1)
        lon_lat = (123.4, -67.8)
        (x, y) = pp.lon_lat_to_xy(lon_lat)
        assert str(x)[:7] == '11377.5'
        assert str(y)[:10] == '5917.5'

    def test_xy_to_lon_lat(self):
        pp = PointPicker(random_seed=1)
        x_y = (11377.5, 5917.5)
        (lon, lat) = pp.xy_to_lon_lat(x_y)
        assert str(lon)[:5] == '123.4'
        assert str(lat)[:5] == '-67.8'
