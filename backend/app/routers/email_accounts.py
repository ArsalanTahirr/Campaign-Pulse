"""
routers/email_accounts.py — Sender account and warmup management endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.schemas.email_accounts import (
    SenderAccountCreate,
    SenderAccountOut,
    SenderAccountUpdate,
    WarmupSettingsOut,
    WarmupSettingsPatch,
)
from app.services import email_account_service

router = APIRouter()


@router.get("/email-accounts", response_model=list[SenderAccountOut])
def list_email_accounts(
    workspace_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    return email_account_service.list_accounts(workspace_id, db)


@router.post("/email-accounts", response_model=SenderAccountOut, status_code=status.HTTP_201_CREATED)
def create_email_account(
    workspace_id: str,
    body: SenderAccountCreate,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    return email_account_service.create_account(
        workspace_id=workspace_id,
        payload=body.model_dump(exclude_none=True),
        db=db,
    )


@router.patch("/email-accounts/{account_id}", response_model=SenderAccountOut)
def update_email_account(
    workspace_id: str,
    account_id: str,
    body: SenderAccountUpdate,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    return email_account_service.update_account(
        workspace_id=workspace_id,
        account_id=account_id,
        updates=body.model_dump(exclude_unset=True),
        db=db,
    )


@router.delete("/email-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_account(
    workspace_id: str,
    account_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    email_account_service.delete_account(workspace_id, account_id, db)


@router.patch("/email-accounts/{account_id}/warmup", response_model=WarmupSettingsOut)
def patch_warmup(
    workspace_id: str,
    account_id: str,
    body: WarmupSettingsPatch,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    return email_account_service.patch_warmup_settings(
        workspace_id=workspace_id,
        account_id=account_id,
        payload=body.model_dump(exclude_unset=True),
        db=db,
    )
