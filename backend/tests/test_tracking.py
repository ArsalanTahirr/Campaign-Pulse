from urllib.parse import quote

from app.models import EmailEvent
from app.services.tracking_service import sign_click_target
from tests.factories import (
    attach_sender_to_campaign,
    make_campaign,
    make_lead,
    make_sender_account,
    make_step,
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
