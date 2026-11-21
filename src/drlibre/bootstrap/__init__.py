# Interfaces name the signed-in creator of new records through bootstrap, not persistence.
from drlibre.persistence.provenance import act_as, stop_acting

__all__ = ["act_as", "stop_acting"]
