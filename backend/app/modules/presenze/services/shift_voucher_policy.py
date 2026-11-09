"""Voucher eligibility follows the dated profile, independently of the day's schedule."""

from app.modules.presenze.services.personnel_profiles import technician_profile
from app.modules.presenze.services.shift_assignments import shift_assignment_values


def shift_voucher_profile(record):
    assignment = shift_assignment_values(record)
    if assignment["shift_worker_source"] is not None and assignment["shift_worker_type"] == "none":
        return False
    return technician_profile(record) is not None or assignment["shift_worker_type"] in {
        "acquaiolo",
        "telecontrollo",
    }
