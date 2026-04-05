"""Tests for GAIA Operazioni module — unit tests (no DB required)."""

from decimal import Decimal

import pytest

from app.modules.operazioni.services.attachment_service import (
    get_attachment_type,
    get_file_extension,
    compute_checksum,
)
from app.modules.operazioni.schemas.vehicles import (
    VehicleCreate,
    VehicleUpdate,
    VehicleAssignmentCreate,
    VehicleUsageSessionStart,
    VehicleUsageSessionStop,
    VehicleFuelLogCreate,
    VehicleMaintenanceCreate,
    VehicleOdometerReadingCreate,
)


class TestAttachmentTypeDetection:
    def test_image_types(self):
        assert get_attachment_type("image/jpeg") == "image"
        assert get_attachment_type("image/png") == "image"
        assert get_attachment_type("image/gif") == "image"
        assert get_attachment_type("image/webp") == "image"

    def test_audio_types(self):
        assert get_attachment_type("audio/mpeg") == "audio"
        assert get_attachment_type("audio/wav") == "audio"
        assert get_attachment_type("audio/ogg") == "audio"

    def test_video_types(self):
        assert get_attachment_type("video/mp4") == "video"
        assert get_attachment_type("video/quicktime") == "video"

    def test_document_types(self):
        assert get_attachment_type("application/pdf") == "document"
        assert get_attachment_type("application/msword") == "document"


class TestFileExtension:
    def test_with_extension(self):
        assert get_file_extension("photo.jpg") == "jpg"
        assert get_file_extension("document.PDF") == "pdf"

    def test_no_extension(self):
        assert get_file_extension("noext") is None


class TestChecksum:
    def test_deterministic(self):
        data = b"test data"
        assert compute_checksum(data) == compute_checksum(data)

    def test_different_data(self):
        assert compute_checksum(b"data1") != compute_checksum(b"data2")


class TestVehicleSchemas:
    def test_vehicle_create_valid(self):
        data = VehicleCreate(code="V-001", name="Test", vehicle_type="auto")
        assert data.code == "V-001"
        assert data.has_gps_device is False

    def test_vehicle_create_with_gps(self):
        data = VehicleCreate(
            code="V-002", name="Test", vehicle_type="auto", has_gps_device=True
        )
        assert data.has_gps_device is True

    def test_vehicle_update_partial(self):
        data = VehicleUpdate(notes="Updated notes")
        assert data.plate_number is None
        assert data.notes == "Updated notes"

    def test_assignment_create_operator(self):
        from datetime import datetime
        from uuid import uuid4

        data = VehicleAssignmentCreate(
            assignment_target_type="operator",
            operator_user_id=1,
            start_at=datetime.now(),
        )
        assert data.assignment_target_type == "operator"

    def test_assignment_create_team(self):
        from datetime import datetime
        from uuid import uuid4

        data = VehicleAssignmentCreate(
            assignment_target_type="team",
            team_id=uuid4(),
            start_at=datetime.now(),
        )
        assert data.assignment_target_type == "team"

    def test_usage_session_start(self):
        from datetime import datetime
        from uuid import uuid4

        data = VehicleUsageSessionStart(
            vehicle_id=uuid4(),
            started_at=datetime.now(),
            start_odometer_km=Decimal("1000.0"),
        )
        assert data.start_odometer_km == Decimal("1000.0")

    def test_usage_session_stop(self):
        from datetime import datetime

        data = VehicleUsageSessionStop(
            ended_at=datetime.now(),
            end_odometer_km=Decimal("1050.0"),
        )
        assert data.end_odometer_km == Decimal("1050.0")

    def test_fuel_log_create(self):
        from datetime import datetime

        data = VehicleFuelLogCreate(
            fueled_at=datetime.now(),
            liters=Decimal("35.5"),
            total_cost=Decimal("62.80"),
        )
        assert data.liters == Decimal("35.5")

    def test_maintenance_create(self):
        from datetime import datetime

        data = VehicleMaintenanceCreate(
            title="Tagliando annuale",
            opened_at=datetime.now(),
        )
        assert data.status == "planned"

    def test_odometer_reading_create(self):
        from datetime import datetime

        data = VehicleOdometerReadingCreate(
            reading_at=datetime.now(),
            odometer_km=Decimal("42115.4"),
            source_type="manual",
        )
        assert data.odometer_km == Decimal("42115.4")


class TestBusinessRulesValidation:
    def test_odometer_decreasing_raises(self):
        from app.modules.operazioni.services.vehicle_service import stop_usage_session
        from datetime import datetime

        class MockSession:
            def __init__(self):
                self.id = "test"
                self.vehicle_id = "test"
                self.status = "open"
                self.start_odometer_km = Decimal("1000.0")
                self.ended_at = None
                self.actual_driver_user_id = 1
                self.started_by_user_id = 1

        class MockDB:
            def get(self, model, id):
                return None

            def add(self, obj):
                pass

            def flush(self):
                pass

        mock_session = MockSession()
        mock_db = MockDB()

        with pytest.raises(ValueError, match="End odometer cannot be less"):
            stop_usage_session(
                mock_db,
                mock_session,
                {
                    "ended_at": datetime.now(),
                    "end_odometer_km": Decimal("900.0"),
                },
            )

    def test_session_not_open_raises(self):
        from app.modules.operazioni.services.vehicle_service import stop_usage_session

        class MockSession:
            def __init__(self):
                self.status = "closed"

        class MockDB:
            pass

        with pytest.raises(ValueError, match="Session is not open"):
            stop_usage_session(
                MockDB(),
                MockSession(),
                {
                    "end_odometer_km": Decimal("1050.0"),
                },
            )

    def test_deactivate_with_open_session_raises(self):
        from app.modules.operazioni.services.vehicle_service import deactivate_vehicle

        class MockVehicle:
            def __init__(self):
                self.id = "test"
                self.is_active = True
                self.current_status = "available"
                self.updated_by_user_id = None

        class MockDB:
            def scalar(self, query):
                return "open_session"

            def flush(self):
                pass

        with pytest.raises(
            ValueError, match="Cannot deactivate vehicle with open usage session"
        ):
            deactivate_vehicle(MockDB(), MockVehicle())
