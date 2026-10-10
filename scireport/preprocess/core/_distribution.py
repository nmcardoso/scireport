"""Sample helpers shared by the Q-Q and P-P plots: finite samples and the normal distribution.

The normal quantile function and distribution function come from the standard library
(:class:`statistics.NormalDist` and :func:`math.erf`), so the base install needs no scipy.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pyarrow as pa

from scireport.preprocess.plotting import numbers

_NORMAL = NormalDist()


def finite_sample(table: pa.Table, column: str) -> np.ndarray:
  """Return the finite values of a numeric column, sorted.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  column : str
      A numeric column; nulls, NaN and infinities are dropped.

  Returns
  -------
  numpy.ndarray
      The values in increasing order.
  """
  values = numbers(table, column)
  return np.sort(values[np.isfinite(values)])


def standardise(values: np.ndarray) -> np.ndarray:
  """Centre a sample on its mean and scale it to unit standard deviation.

  Parameters
  ----------
  values : numpy.ndarray
      The sample.

  Returns
  -------
  numpy.ndarray
      ``(values - mean) / std`` (population standard deviation); zeros when the sample is
      constant.
  """
  if values.size == 0:
    return values
  spread = float(np.std(values))
  if not spread > 0.0:
    return np.zeros_like(values)
  return (values - float(np.mean(values))) / spread


def normal_ppf(levels: np.ndarray) -> np.ndarray:
  """Return quantiles of the standard normal distribution.

  Parameters
  ----------
  levels : numpy.ndarray
      Probabilities strictly between 0 and 1.

  Returns
  -------
  numpy.ndarray
      The value ``z`` with ``P(Z <= z) = level`` for each level.
  """
  return np.array([_NORMAL.inv_cdf(float(level)) for level in levels], dtype=float)


def normal_cdf(values: np.ndarray) -> np.ndarray:
  """Return the standard normal distribution function.

  Parameters
  ----------
  values : numpy.ndarray
      Points on the real line.

  Returns
  -------
  numpy.ndarray
      ``P(Z <= value)`` for each value.
  """
  return np.array([0.5 * (1.0 + math.erf(float(v) / math.sqrt(2.0))) for v in values], dtype=float)


def hazen_levels(count: int) -> np.ndarray:
  """Return ``count`` plotting positions ``(i + 0.5) / count``.

  Parameters
  ----------
  count : int
      Number of levels, at least 1.

  Returns
  -------
  numpy.ndarray
      Probabilities strictly inside (0, 1), increasing.
  """
  return (np.arange(count, dtype=float) + 0.5) / max(count, 1)
