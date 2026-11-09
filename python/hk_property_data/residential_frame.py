"""Pandas-first analysis over the shared, immutable Arrow session snapshot.

Pandas and PyArrow load on data access, never on import or construction.
"""
from .cloud import CloudDataError
from .residential import _normalise_series, _prepare_read
from .residential_groups import group_for, normalise_groups, normalise_frequency


def _catalogue(table):
    import pandas as pd

    fields = ['metric_id', 'metric_name', 'unit', 'frequency', 'source_name',
              'source_url', 'date', 'value']
    frame = table.select(fields).to_pandas(date_as_object=False)
    if frame.duplicated(['metric_id', 'date']).any():
        raise CloudDataError('Duplicate metric/date observations cannot form an unambiguous history')
    grouped = frame.groupby('metric_id', observed=True, sort=True)
    for field in ('metric_name', 'unit', 'frequency'):
        if (grouped[field].nunique(dropna=False) > 1).any():
            raise CloudDataError(f'Conflicting {field} definitions for one metric ID')

    def distinct(values):
        return '; '.join(sorted(set(values)))

    result = grouped.agg(
        metric_name=('metric_name', 'first'), unit=('unit', 'first'),
        frequency=('frequency', 'first'), sources=('source_name', distinct),
        source_urls=('source_url', distinct), first_date=('date', 'min'),
        last_date=('date', 'max'), observations=('date', 'size'),
        non_missing=('value', 'count'))
    result.index = pd.Index(result.index.astype(str), name='metric_id')
    result['group'] = result.index.map(group_for)
    return result


def _generation(table):
    return (table.schema.metadata or {}).get(b'hk_property_data.generated_at', b'').decode() or None


class Residential:
    """A lazy analysis object for one, several, or all residential indicators.

    Examples: Residential().overview();
    Residential(group='Price indices').history(start='2025-01').
    Explicit series IDs remain supported, including a positional iterable.
    Objects share the same bounded session snapshot; refresh=True replaces it.
    """

    def __init__(self, series=None, *, group=None, frequency=None):
        self._series = _normalise_series(series)
        self._groups = normalise_groups(group)
        self._frequency = normalise_frequency(frequency)

    def _read(self, series, start, end, timeout, refresh, cache, *, group=None, frequency=None):
        selected = self._series if series is None else series
        groups = self._groups if group is None else normalise_groups(group)
        frequency = self._frequency if frequency is None else normalise_frequency(frequency)
        table, selected, first, last = _prepare_read(
            series=selected, start=start, end=end, timeout=timeout, refresh=refresh, cache=cache)
        from .residential_parquet import select_table
        available = set(table['metric_id'].unique().to_pylist())
        if selected is not None:
            missing = set(selected) - available
            if missing:
                raise ValueError('Unknown metric IDs: ' + ', '.join(sorted(missing)) + '; inspect Residential().catalog()')
        if groups is not None:
            selected = tuple(metric for metric in (sorted(available) if selected is None else selected)
                             if group_for(metric) in groups)
            if not selected:
                raise ValueError('No indicators match the selected group and series; inspect Residential().overview()')
        source = select_table(table, selected, '0001-01-01', '9999-12-31')
        catalog = _catalogue(source)
        if selected is not None:
            catalog = catalog.reindex(selected)
        if frequency is not None:
            catalog = catalog.loc[catalog['frequency'].eq(frequency)]
            if catalog.empty:
                raise ValueError('No indicators match the selected frequency; inspect Residential().overview()')
            source = select_table(source, tuple(catalog.index), '0001-01-01', '9999-12-31')
        filtered = select_table(source, None, first, last)
        return filtered, catalog

    def history(self, *, series=None, group=None, frequency=None, start=None, end=None, labels='name',
                timeout=90, refresh=False, cache=True):
        """Return float64 indicator columns on a sorted Date DatetimeIndex.

        Bounds are inclusive. Missing/unobserved values are NaN; observations are
        never resampled or filled. Units/frequencies are in attrs['series'] and
        catalog(); per-observation flags and notes are in observations().
        labels='id' selects stable IDs instead of human-readable column names.
        group accepts a name or iterable of names (union). Group, frequency and
        series selectors intersect; frequency filters never resample observations.
        Non-None method selectors override their corresponding constructor defaults.
        """
        if labels not in ('name', 'id'):
            raise ValueError("labels must be 'name' or 'id'")
        table, catalog = self._read(series, start, end, timeout, refresh, cache,
                                    group=group, frequency=frequency)
        import pandas as pd

        values = table.select(['date', 'metric_id', 'value']).to_pandas(date_as_object=False)
        values['metric_id'] = values['metric_id'].astype(str)
        result = values.pivot(index='date', columns='metric_id', values='value')
        result = result.reindex(columns=catalog.index).sort_index().astype('float64')
        result.index = pd.DatetimeIndex(result.index, name='Date')
        names = catalog['metric_name'].astype(str)
        duplicated = names.duplicated(keep=False)
        columns = [metric if labels == 'id' else
                   f'{names.loc[metric]} [{metric}]' if duplicated.loc[metric] else names.loc[metric]
                   for metric in catalog.index]
        if len(columns) != len(set(columns)):
            raise CloudDataError("Ambiguous display labels; use labels='id'")
        result.columns = columns
        result.attrs = dict(data_generated_at=_generation(table), series={
            column: dict(metric_id=metric, **{field: catalog.loc[metric, field]
                         for field in ('metric_name', 'unit', 'frequency', 'sources', 'source_urls', 'group')})
            for column, metric in zip(columns, catalog.index)})
        return result

    def catalog(self, *, series=None, group=None, frequency=None, timeout=90, refresh=False, cache=True):
        """Return names, groups, units, original frequencies, sources and coverage.

        Date coverage includes recorded missing values. None inherits the
        corresponding constructor selector; use Residential() for an unbound view.
        """
        table, catalog = self._read(series, None, None, timeout, refresh, cache,
                                    group=group, frequency=frequency)
        catalog.attrs['data_generated_at'] = _generation(table)
        return catalog

    def overview(self, *, series=None, group=None, frequency=None, timeout=90, refresh=False, cache=True):
        """Return a compact DataFrame indexed by group and original frequency.

        Reports indicator count, source records, non-null values and the union of
        recorded dates. Members can have different coverage and missing values.
        Counts concern source records, not blanks introduced by history alignment.
        This method covers full history; use history(start=..., end=...) for dates.
        """
        catalog = self.catalog(series=series, group=group, frequency=frequency,
                               timeout=timeout, refresh=refresh, cache=cache)
        result = catalog.groupby(['group', 'frequency'], observed=True, sort=True).agg(
            indicators=('metric_name', 'size'), records=('observations', 'sum'),
            available_values=('non_missing', 'sum'), first_date=('first_date', 'min'),
            last_date=('last_date', 'max'))
        result.attrs['data_generated_at'] = catalog.attrs['data_generated_at']
        return result

    def observations(self, *, series=None, group=None, frequency=None, start=None, end=None,
                     timeout=90, refresh=False, cache=True):
        """Return typed long records including per-observation status and notes."""
        table, _ = self._read(series, start, end, timeout, refresh, cache,
                              group=group, frequency=frequency)
        # A writable independent result, including with pandas versions without
        # copy-on-write. Caller edits cannot reach immutable cached Arrow buffers.
        result = table.to_pandas(date_as_object=False).copy(deep=True)
        result.attrs['data_generated_at'] = _generation(table)
        return result
