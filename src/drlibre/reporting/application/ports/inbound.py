from typing import Protocol

from drlibre.reporting.domain.dashboard import Dashboard, Range, Ratio
from drlibre.shared_kernel.ids import Id

__all__ = ["Dashboard", "Range", "Ratio", "ViewDashboard"]


class ViewDashboard(Protocol):
    def execute(self, *, actor_id: Id, period: Range) -> Dashboard:
        """Spec 13 figures over every hospital; forbidden unless the actor is an admin."""
        ...
