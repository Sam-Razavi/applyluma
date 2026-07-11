"""Tests for crud_application._validate_owned_references.

ApplicationUpdate/ApplicationCreate let a client supply cv_id/job_description_id
directly — without an ownership check, a client could point their own
application at another user's CV or job description by UUID.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import application as crud_application

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CV_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
JD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _db(found: bool) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = ("row",) if found else None
    return db


def test_validate_owned_references_passes_when_cv_is_owned() -> None:
    db = _db(found=True)
    crud_application._validate_owned_references(db, USER_ID, {"cv_id": CV_ID})  # must not raise


def test_validate_owned_references_rejects_unowned_cv() -> None:
    db = _db(found=False)
    with pytest.raises(crud_application.ForeignReferenceNotOwnedError, match="cv_id"):
        crud_application._validate_owned_references(db, USER_ID, {"cv_id": CV_ID})


def test_validate_owned_references_passes_when_job_description_is_owned() -> None:
    db = _db(found=True)
    crud_application._validate_owned_references(
        db, USER_ID, {"job_description_id": JD_ID}
    )  # must not raise


def test_validate_owned_references_rejects_unowned_job_description() -> None:
    db = _db(found=False)
    with pytest.raises(crud_application.ForeignReferenceNotOwnedError, match="job_description_id"):
        crud_application._validate_owned_references(db, USER_ID, {"job_description_id": JD_ID})


def test_validate_owned_references_ignores_absent_fields() -> None:
    db = MagicMock()
    crud_application._validate_owned_references(db, USER_ID, {"company_name": "Acme"})
    db.query.assert_not_called()


def test_validate_owned_references_ignores_none_values() -> None:
    db = MagicMock()
    crud_application._validate_owned_references(
        db, USER_ID, {"cv_id": None, "job_description_id": None}
    )
    db.query.assert_not_called()
