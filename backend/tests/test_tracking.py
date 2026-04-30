from urllib.parse import quote
import uuid

from app.models import EmailEvent
from app.services import sending_engine_service
from app.services.tracking_service import sign_click_target
from tests.factories import (
    attach_sender_to_campaign,
    make_campaign,
    make_lead,
    make_sender_account,
    make_step,
    make_step_email,
    make_user,
    make_workspace,
)


def test_open_and_click_tracking_create_events(client, db):
    user = make_user(db)
    ws = make_workspace(db, user)
    campaign = make_campaign(db, ws.workspace_id, name="Track Campaign", status="active")
    lead = make_lead(db, campaign.campaign_id)
    step = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws.workspace_id, email="sender_track@example.com")
    attach_sender_to_campaign(db, campaign.campaign_id, sender.account_id)
    sent_event = EmailEvent(
        lead_id=lead.lead_id,
        step_id=step.step_id,
        event_type="sent",
        event_scope="lead",
        sender_account_id=sender.account_id,
    )
    db.add(sent_event)
    db.commit()
    db.refresh(sent_event)

    open_res = client.get(f"/track/open/{sent_event.event_id}")
    assert open_res.status_code == 200
    assert open_res.headers["content-type"].startswith("image/gif")
    opened = db.query(EmailEvent).filter(EmailEvent.event_type == "opened").all()
    assert len(opened) == 1
    assert opened[0].lead_id == lead.lead_id

    target = "https://example.com/offer"
    sig = sign_click_target(sent_event.event_id, target)
    click_res = client.get(
        f"/track/click/{sent_event.event_id}?u={quote(target, safe='')}&sig={sig}",
        follow_redirects=False,
    )
    assert click_res.status_code == 302
    assert click_res.headers["location"] == target
    clicked = db.query(EmailEvent).filter(EmailEvent.event_type == "clicked").all()
    assert len(clicked) == 1
    assert clicked[0].event_metadata["url"] == target


def test_click_tracking_rejects_bad_signature(client, db):
    user = make_user(db)
    ws = make_workspace(db, user)
    campaign = make_campaign(db, ws.workspace_id, name="Track Campaign 2", status="active")
    lead = make_lead(db, campaign.campaign_id)
    sent_event = EmailEvent(
        lead_id=lead.lead_id,
        event_type="sent",
        event_scope="lead",
    )
    db.add(sent_event)
    db.commit()
    db.refresh(sent_event)

    target = "https://example.com/offer"
    bad = client.get(f"/track/click/{sent_event.event_id}?u={quote(target, safe='')}&sig=invalid")
    assert bad.status_code == 403


def test_process_claimed_lead_renders_merge_tags_from_custom_variables(db, monkeypatch):
    user = make_user(db)
    ws = make_workspace(db, user)
    campaign = make_campaign(db, ws.workspace_id, name="Merge Campaign", status="active")
    step = make_step(db, campaign.campaign_id, step_number=1)
    make_step_email(
        db,
        step.step_id,
        subject="Hi {{first_name}} from {{company}}",
        body="<p>{{first_name}} {{last_name}} - {{job_title}} - {{missing_key}}</p>",
    )
    sender = make_sender_account(db, ws.workspace_id, email="sender_merge@example.com")
    attach_sender_to_campaign(db, campaign.campaign_id, sender.account_id)

    lead = make_lead(db, campaign.campaign_id, email="lead_merge@example.com")
    lead.first_name = "Ava"
    lead.last_name = "Stone"
    lead.custom_variables = {"company": "Acme", "job_title": "Founder"}
    lead.delivery_state = "sending"
    lock_token = str(uuid.uuid4())
    lead.lock_token = lock_token
    lead.next_step_id = step.step_id
    db.commit()

    captured = {}

    def _fake_send_smtp(account, recipient, subject, html_body, plain_body=""):
        captured["recipient"] = recipient
        captured["subject"] = subject
        captured["html_body"] = html_body
        return "<message-id>"

    monkeypatch.setattr(sending_engine_service, "_send_smtp", _fake_send_smtp)

    sending_engine_service.process_claimed_lead(lead.lead_id, lock_token, db)
    db.refresh(lead)

    assert captured["recipient"] == "lead_merge@example.com"
    assert captured["subject"] == "Hi Ava from Acme"
    assert "<p>Ava Stone - Founder - </p>" in captured["html_body"]
    assert "{{" not in captured["html_body"]
    assert lead.delivery_state == "sent"
