"""
routers/track.py — Public tracking endpoints for opens and clicks.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import tracking_service

router = APIRouter()

_PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


@router.get("/open/{event_id}")
def track_open(event_id: str, request: Request, db: Session = Depends(get_db)):
    tracking_service.log_open_event(event_id, request, db)
    return Response(content=_PIXEL_GIF, media_type="image/gif")


@router.get("/click/{event_id}")
def track_click(
    event_id: str,
    request: Request,
    u: str = Query(..., description="URL encoded destination URL"),
    sig: str = Query(..., description="HMAC signature of destination URL"),
    db: Session = Depends(get_db),
):
    target = tracking_service.decode_click_target(u)
    if not tracking_service.verify_click_signature(event_id, target, sig):
        return Response(status_code=403, content="Invalid tracking signature.")
    tracking_service.log_click_event(event_id, target, request, db)
    return RedirectResponse(url=target, status_code=302)
