"""
Unit tests for Pydantic validators on RecordCreate and RecordUpdate.
Paper applied: Scalable REST APIs 2024 — input validation as a reliability concern
"""
import pytest
from pydantic import ValidationError
from datetime import date
from app.api.v1.records import RecordCreate, RecordUpdate


class TestRecordCreate:
    def _valid(self, **overrides):
        base = dict(
            amount=100.00,
            type="income",
            category="salary",
            record_date=date.today(),
        )
        base.update(overrides)
        return base

    def test_valid_record_passes(self):
        r = RecordCreate(**self._valid())
        assert r.category == "salary"
        assert float(r.amount) == 100.0

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            RecordCreate(**self._valid(amount=-50))

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            RecordCreate(**self._valid(amount=0))

    def test_blank_category_rejected(self):
        with pytest.raises(ValidationError):
            RecordCreate(**self._valid(category="   "))

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            RecordCreate(**self._valid(type="transfer"))

    def test_category_normalized_to_lowercase(self):
        r = RecordCreate(**self._valid(category="  Food & Dining  "))
        assert r.category == "food & dining"

    def test_expense_type_valid(self):
        r = RecordCreate(**self._valid(type="expense"))
        assert r.type == "expense"

    def test_notes_optional(self):
        r = RecordCreate(**self._valid())
        assert r.notes is None

    def test_notes_accepted_when_provided(self):
        r = RecordCreate(**self._valid(notes="Monthly salary"))
        assert r.notes == "Monthly salary"


class TestRecordUpdate:
    def test_all_none_creates_empty_model(self):
        r = RecordUpdate()
        assert r.model_dump(exclude_none=True) == {}

    def test_partial_update_valid(self):
        r = RecordUpdate(category="utilities")
        assert r.category == "utilities"

    def test_negative_amount_rejected_in_update(self):
        with pytest.raises(ValidationError):
            RecordUpdate(amount=-10)

    def test_blank_category_rejected_in_update(self):
        with pytest.raises(ValidationError):
            RecordUpdate(category="")
