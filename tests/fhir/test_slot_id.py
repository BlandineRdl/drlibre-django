import re
from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from drlibre.interfaces.fhir.slot_id import SlotKey, slot_id, slot_key
from drlibre.shared_kernel.ids import Id

_FHIR_ID = re.compile(r"[A-Za-z0-9\-.]{1,64}")
starts = st.integers(0, 2**31).map(lambda m: datetime.fromtimestamp(m * 60, UTC))
uuids = st.uuids().map(Id)


@given(clinician=uuids, kind=uuids, start=starts)
def test_a_slot_id_is_a_fhir_id_that_gives_back_its_clinician_type_and_start(
    clinician: Id, kind: Id, start: datetime
) -> None:
    """Spec §15.6 : un id de `Slot` est stable pour un même praticien, type et début."""
    key = SlotKey(clinician, kind, start)
    found = slot_id(key)
    assert _FHIR_ID.fullmatch(found)
    assert len(found) == 58
    assert slot_key(found) == key
    assert slot_id(SlotKey(clinician, kind, start)) == found


@given(raw=st.text(max_size=70))
def test_a_malformed_slot_id_names_no_slot(raw: str) -> None:
    """Spec §15.1 : un id de `Slot` mal formé ne désigne aucun créneau."""
    key = slot_key(raw)
    assert key is None or slot_id(key) == raw
