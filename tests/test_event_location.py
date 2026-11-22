import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from event_location import REGION_REFERENCE_POINTS, geocode_address, nearest_region


class NearestRegionTests(unittest.TestCase):
    def test_reference_points_resolve_to_their_own_region(self):
        for region, coordinates in REGION_REFERENCE_POINTS.items():
            with self.subTest(region=region):
                self.assertEqual(nearest_region(*coordinates), region)

    def test_coordinates_outside_singapore_are_not_assigned(self):
        self.assertIsNone(nearest_region(0.0, 0.0))

    def test_address_lookup_is_limited_to_singapore(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = (
            b'[{"lat":"1.35735","lon":"103.94","display_name":"Singapore"}]'
        )
        with (
            patch("event_location.urlopen", return_value=response) as urlopen,
            patch("event_location.time.monotonic", return_value=100.0),
            patch("event_location._LAST_GEOCODING_REQUEST", 0.0),
        ):
            coordinates = geocode_address("Example address")

        request = urlopen.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(coordinates, (1.35735, 103.94))
        self.assertEqual(query["countrycodes"], ["sg"])
        self.assertEqual(request.get_header("User-agent"), "ClaritySG/1.0")


if __name__ == "__main__":
    unittest.main()
