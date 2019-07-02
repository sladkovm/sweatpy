from sweat.io import fit
from sweat.io.models import dataframes
import numpy as np


def test_load():
    wdf = fit.load('tests/fixtures/fit/2018-03-13-18-17-02.fit')

    assert isinstance(wdf, dataframes.WorkoutDataFrame)
    assert 'heartrate' in wdf.columns
    assert 'power' in wdf.columns
    assert 'cadence' in wdf.columns
    assert 'distance' in wdf.columns
    assert wdf.index.dtype == np.dtype('int64')
    assert len(wdf) == 4365
