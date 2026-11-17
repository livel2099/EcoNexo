import unittest
from app.brazil_alerts import contains, fire_features, deforestation_features, locate


class BrazilAlertsTests(unittest.TestCase):
    def test_boundary_excludes_other_states(self):
        self.assertIsNotNone(locate(-56.0974, -15.6014))  # Cuiabá
        self.assertIsNone(locate(-54.646, -20.469))  # Campo Grande, MS
        self.assertIsNone(locate(-55.9, -27.3))  # Misiones

    def test_polygon_holes(self):
        geometry = {"type": "Polygon", "coordinates": [
            [[0,0],[10,0],[10,10],[0,10],[0,0]],
            [[4,4],[6,4],[6,6],[4,6],[4,4]]]}
        self.assertTrue(contains(geometry, 2, 2))
        self.assertFalse(contains(geometry, 5, 5))

    def test_firms_deduplicates_and_rejects_invalid_rows(self):
        header = "latitude,longitude,acq_date,acq_time,confidence\n"
        row = "-15.6014,-56.0974,2026-11-17,0315,n\n"
        features, skipped = fire_features(header + row + row +
            "-20.469,-54.646,2026-11-17,0315,h\n" +
            "-15.6,-56.1,bad,0315,h\n" +
            "nan,-56.1,2026-11-17,0315,h\n", "VIIRS_SNPP_NRT")
        self.assertEqual(len(features), 1)
        self.assertEqual(skipped, 2)
        self.assertEqual(features[0]["properties"]["observed_at"], "2026-11-17T03:15:00+00:00")
        self.assertEqual(features[0]["properties"]["municipality_code"], "5103403")

    def test_provider_error_is_not_empty_success(self):
        with self.assertRaises(ValueError):
            fire_features("Invalid MAP_KEY", "VIIRS_SNPP_NRT")
        features, skipped = fire_features("latitude,longitude,acq_date,acq_time\n", "VIIRS_SNPP_NRT")
        self.assertEqual((features, skipped), ([], 0))

    def test_deter_names_and_classes(self):
        feature = {"id": "a", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,0]]]},
            "properties": {"uf": "MT", "municipality": "CUIABA", "classname": "DESMATAMENTO_CR", "view_date": "2026-11-16"}}
        rows, skipped = deforestation_features([feature], "INPE")
        self.assertEqual(skipped, 0)
        self.assertEqual(rows[0]["properties"]["municipality_code"], "5103403")
        feature["properties"]["classname"] = "CICATRIZ_DE_QUEIMADA"
        self.assertEqual(deforestation_features([feature], "INPE")[0], [])
        feature["properties"]["classname"] = "DESMATAMENTO_CR"
        feature["properties"]["uf"] = "MS"
        self.assertEqual(deforestation_features([feature], "INPE")[0], [])


if __name__ == "__main__":
    unittest.main()
