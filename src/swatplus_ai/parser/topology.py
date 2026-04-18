"""Topology helpers derived from parsed TxtInOut connectivity tables.

The connectivity (``*.con``) files already encode the SWAT+ spatial
graph — HRUs feed routing units, which feed channels, which may feed
further channels / reservoirs / aquifers. For downstream code (figures,
calibration targets, upstream-aggregation queries) we don't want each
caller to re-interpret ``out_tot`` and the trailing connection tuples
— :class:`TopologyAccessor` wraps a parsed :class:`TxtInOutProject` and
exposes the most common graph-level questions as one-line methods.

Slice A only needs the single question "which channels are outfalls?"
— a channel is an outfall iff its ``out_tot == 0`` (no downstream
receivers). On the URU fixture this should return exactly ``["cha033"]``.
Future slices will extend this accessor with upstream / subbasin /
tributary helpers as the need arises.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swatplus_ai.parser.txtinout import TxtInOutProject


class TopologyAccessor:
    """Graph-level queries over a parsed :class:`TxtInOutProject`."""

    def __init__(self, project: TxtInOutProject) -> None:
        self._project = project

    def outfall_channels(self) -> tuple[str, ...]:
        """Return the names of channels with no downstream receiver.

        Reads the already-parsed ``chandeg.con`` and selects rows whose
        ``out_tot`` is ``0``. Returns an empty tuple when the project
        has no ``chandeg.con`` (channels-free projects), and preserves
        the order channels appear in the file.
        """
        chandeg = self._project.chandeg_con
        if chandeg is None:
            return ()
        return tuple(row.name for row in chandeg.rows if row.out_tot == 0)


__all__ = ["TopologyAccessor"]
