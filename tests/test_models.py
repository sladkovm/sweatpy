import unittest

import numpy as np
import pandas as pd

from athletic_pandas import exceptions, models


class TestDataPoint(unittest.TestCase):
    def test_init(self):
        p = models.DataPoint(1, 2)

        self.assertEqual(p, (1, 2))
        self.assertEqual(p.index, 1)
        self.assertEqual(p.value, 2)

    def test_init_missing_values(self):
        with self.assertRaises(TypeError):
            models.DataPoint()

    def test_init_too_many_values(self):
        with self.assertRaises(TypeError):
            models.DataPoint(1, 2, 3)


class TestAthlete(unittest.TestCase):
    def setUp(self):
        self.athlete = models.Athlete(name='Chris', ftp=300)

    def test_empty_init(self):
        athlete = models.Athlete()
        self.assertTrue(hasattr(athlete, 'name'))
        self.assertTrue(hasattr(athlete, 'sex'))
        self.assertTrue(hasattr(athlete, 'weight'))
        self.assertTrue(hasattr(athlete, 'dob'))
        self.assertTrue(hasattr(athlete, 'ftp'))
        self.assertTrue(hasattr(athlete, 'cp'))
        self.assertTrue(hasattr(athlete, 'w_prime'))

    def test_init(self):
        self.assertEqual(self.athlete.name, 'Chris')
        self.assertEqual(self.athlete.ftp, 300)


class TestWorkoutDataFrame(unittest.TestCase):
    def setUp(self):
        data = {
            'time': range(10),
            'heartrate': range(10),
            'power': range(10)}
        athlete = models.Athlete(name='Chris', weight=80, ftp=300)
        self.wdf = models.WorkoutDataFrame(data)
        self.wdf = self.wdf.set_index('time')
        self.wdf.athlete = athlete

    def _import_csv_as_wdf(self, filename='workout_1.csv'):
        athlete = self.wdf.athlete
        self.wdf = models.WorkoutDataFrame(
            pd.read_csv('tests/example_files/{}'.format(filename)))
        self.wdf = self.wdf.set_index('time')
        self.wdf.athlete = athlete

    def test_empty_init(self):
        wdf = models.WorkoutDataFrame()

        self.assertIsInstance(wdf, pd.DataFrame)
        self.assertIsInstance(wdf, models.WorkoutDataFrame)

    def test_init(self):
        self.assertTrue('power' in list(self.wdf))
        self.assertTrue('heartrate' in list(self.wdf))
        self.assertEqual(len(self.wdf), 10)
        self.assertTrue(hasattr(self.wdf, 'athlete'))
    
    def test_slicing(self):
        new_wdf = self.wdf[1:5]

        self.assertTrue(isinstance(new_wdf, models.WorkoutDataFrame))
    
    def test_metadata_propagation(self):
        self.assertEqual(self.wdf[1:5].athlete.name, 'Chris')
        self.assertEqual(self.wdf.iloc[[0, 1], :].athlete.name, 'Chris')
        self.assertEqual(self.wdf[['power']].athlete.name, 'Chris')

    def test_is_valid(self):
        self.assertTrue(self.wdf.is_valid())

    def test_is_valid_missing_time_index(self):
        self.wdf.index.name = 'not_time'

        with self.assertRaises(exceptions.WorkoutDataFrameValidationException):
            self.wdf.is_valid()

    def test_is_valid_invalid_sample_rate(self):
        data = {
            'time': range(0, 20, 2),
            'heartrate': range(10),
            'power': range(10)}
        wdf = models.WorkoutDataFrame(data)
        wdf = wdf.set_index('time')

        with self.assertRaisesRegex(
            expected_exception=exceptions.WorkoutDataFrameValidationException,
            expected_regex='[.\n]*Sample rate is not \(consistent\) 1Hz[.\n]*'):
            wdf.is_valid()

    def test_is_valid_invalid_dtype(self):
        data = {
            'time': range(10),
            'heartrate': np.arange(0, 15, 1.5),
            'power': range(10)}
        wdf = models.WorkoutDataFrame(data)
        wdf = wdf.set_index('time')

        with self.assertRaisesRegex(
            expected_exception=exceptions.WorkoutDataFrameValidationException,
            expected_regex='[.\n]*Column \'heartrate\' is not of dtype[.\n]*'):
            wdf.is_valid()

    def test_is_valid_invalid_min_value(self):
        data = {
            'time': range(10),
            'heartrate': range(-10, 0),
            'power': range(10)}
        wdf = models.WorkoutDataFrame(data)
        wdf = wdf.set_index('time')

        with self.assertRaisesRegex(
            expected_exception=exceptions.WorkoutDataFrameValidationException,
            expected_regex='[.\n]*Column \'heartrate\' has values < 0[.\n]*'):
            wdf.is_valid()

    def test_is_valid_invalid_max_value(self):
        data = {
            'time': range(10),
            'heartrate': range(10),
            'power': range(10000, 10010)}
        wdf = models.WorkoutDataFrame(data)
        wdf = wdf.set_index('time')

        with self.assertRaisesRegex(
            expected_exception=exceptions.WorkoutDataFrameValidationException,
            expected_regex='[.\n]*Column \'power\' has values > 3000[.\n]*'):
            wdf.is_valid()

    def test_mean_max_power(self):
        self._import_csv_as_wdf()
        mmp = self.wdf.mean_max_power()

        self.assertEqual(mmp[1], 280)
        self.assertEqual(mmp[300], 209.43666666666667)

    def test_mean_max_power_missing_power(self):
        del self.wdf['power']

        with self.assertRaises(exceptions.MissingDataException):
            self.assertIsNone(self.wdf.mean_max_power())

    def test_weighted_average_power(self):
        self._import_csv_as_wdf()

        self.assertEqual(self.wdf.weighted_average_power(), 156.24624656343036)

    def test_weighted_average_power_missing_weight(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.weight = None

        self.assertEqual(self.wdf.weighted_average_power(), 156.24624656343036)

        with self.assertRaises(exceptions.MissingDataException):
            self.wdf.power_per_kg()

    def test_power_per_kg(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.ftp = 300
        ppkg = self.wdf.power_per_kg()

        self.assertEqual(ppkg[1], 1.1625000000000001)
        self.assertEqual(ppkg[100], 1.0125)

    def test_power_per_kg_missing_weight(self):
        self.wdf.athlete.weight = None

        with self.assertRaises(exceptions.MissingDataException):
            self.wdf.power_per_kg()

    def test_tau_w_prime_balance(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.cp = 200
        self.wdf.athlete.w_prime = 20000
        tau = self.wdf._tau_w_prime_balance()
        self.assertEqual(tau, 482.32071983184653)

    def test_w_prime_balance_waterworth(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.cp = 200
        self.wdf.athlete.w_prime = 20000
        w_balance = self.wdf.w_prime_balance()

        self.assertEqual(len(self.wdf), len(w_balance))
        self.assertEqual(w_balance[0], 20000)
        self.assertEqual(w_balance[2500], 18389.473009018817)
        self.assertEqual(w_balance[3577], 19597.259313320854)

    def test_w_prime_balance_waterworth_2(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.cp = 200
        self.wdf.athlete.w_prime = 20000
        w_balance = self.wdf.w_prime_balance(algorithm='waterworth')

        self.assertEqual(len(self.wdf), len(w_balance))
        self.assertEqual(w_balance[0], 20000)
        self.assertEqual(w_balance[2500], 18389.473009018817)
        self.assertEqual(w_balance[3577], 19597.259313320854)

    def test_w_prime_balance_skiba(self):
        self._import_csv_as_wdf(filename='workout_1_short.csv')
        self.wdf.athlete.cp = 200
        self.wdf.athlete.w_prime = 20000
        w_balance = self.wdf.w_prime_balance(algorithm='skiba')

        self.assertEqual(len(self.wdf), len(w_balance))
        self.assertEqual(w_balance[0], 20000)
        self.assertEqual(w_balance[500], 19031.580246246991)
        self.assertEqual(w_balance[900], 19088.871117462611)

    def test_w_prime_balance_froncioni(self):
        self._import_csv_as_wdf()
        self.wdf.athlete.cp = 200
        self.wdf.athlete.w_prime = 20000
        w_balance = self.wdf.w_prime_balance(algorithm='froncioni')

        self.assertEqual(len(self.wdf), len(w_balance))
        self.assertEqual(w_balance[0], 20000)
        self.assertEqual(w_balance[2500], 19369.652383790162)
        self.assertEqual(w_balance[3577], 19856.860886492974)

    def test_compute_mean_max_bests(self):
        self._import_csv_as_wdf()
        result = self.wdf.compute_mean_max_bests(60, 3)

        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], models.DataPoint)
        self.assertEqual(result[0], (2038, 215.13333333333333))
        self.assertEqual(result[1], (2236, 210.48333333333332))
        self.assertEqual(result[2], (2159, 208.93333333333334))

    def test_compute_mean_max_bests_only_one_result(self):
        self._import_csv_as_wdf()
        result = self.wdf.compute_mean_max_bests(3000, 2)

        self.assertEqual(len(result), 2)
        self.assertNotEqual(result[0], (np.nan, np.nan))
        self.assertEqual(result[1], (np.nan, np.nan))

    def test_compute_mean_max_bests_no_results(self):
        self._import_csv_as_wdf()
        result = self.wdf.compute_mean_max_bests(10000, 1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (np.nan, np.nan))
