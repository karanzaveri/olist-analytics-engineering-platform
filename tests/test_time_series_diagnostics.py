"""Synthetic arithmetic, lag alignment, and boundary sensitivity checks."""

from datetime import date, timedelta
import pytest

from forecasting.time_series_diagnostics import acf_rows, boundary_cases, first_differences, trailing_means, wow_percentages
from forecasting.weekly_revenue import Week


def test_first_differences_align_to_later_week():
    assert first_differences([10, 15, 12, 12]) == [5, -3, 0]
    assert first_differences([10]) == []


def test_wow_percentages_and_zero_denominator():
    assert wow_percentages([100, 150, 75, 0, 10]) == [50, -50, -100, None]
    assert wow_percentages([0, 0]) == [None]


def test_acf_lag_alignment_known_demeaned_values():
    # Centered [-1.5, -0.5, 0.5, 1.5]; covariance denominator = 5.
    rows = acf_rows([1, 2, 3, 4], 10)
    assert [row['lag'] for row in rows] == [0, 1, 2, 3]
    assert [row['acf'] for row in rows] == pytest.approx([1, 0.25, -0.3, -0.45])
    assert [row['overlapping_pairs'] for row in rows] == [4, 3, 2, 1]
    assert [row['acf'] for row in acf_rows([-1, -2, -3, -4], 3)] == pytest.approx([row['acf'] for row in rows])


def test_constant_acf_and_invalid_data():
    assert all(row['acf'] is None for row in acf_rows([5, 5, 5], 2))
    with pytest.raises(ValueError):
        acf_rows([float('nan'), 1], 1)
    with pytest.raises(ValueError):
        acf_rows([1], 1)


def test_excludes_only_flagged_boundary_and_leaves_input_unchanged():
    weeks = [Week(date(2017, 1, 2) + timedelta(weeks=i),
                  date(2017, 1, 8) + timedelta(weeks=i), float(i)) for i in range(86)]
    cases = boundary_cases(weeks)
    assert list(cases.values())[0] == weeks
    assert list(cases.values())[1] == weeks[:-1]
    assert list(cases.values())[1][-1].week_start == date(2018, 8, 13)
    assert len(weeks) == 86


def test_trailing_means_are_descriptive_and_include_current_actual():
    assert trailing_means([1, 2, 3, 4, 5], 4) == [None, None, None, 2.5, 3.5]
