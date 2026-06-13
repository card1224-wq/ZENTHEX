from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

class PushMessage(BaseModel):
    title: str
    body: str
    user_id: str = "all"

# In production, we would use pywebpush to send real VAPID push messages
# Or FCM (Firebase Cloud Messaging) for native mobile apps.
# For MVP, we'll keep a mock log of notifications to be pulled by the frontend.
mock_notifications = []

def send_push_notification(title: str, body: str):
    """Internal function called by Trading Engine to queue a push"""
    print(f"📲 [PUSH 송신] {title} - {body}")
    mock_notifications.append({"title": title, "body": body})
    if len(mock_notifications) > 20:
        mock_notifications.pop(0)

@router.get("/notifications")
async def get_notifications():
    """Endpoint for the PWA to pull the latest notifications"""
    return {"status": "success", "notifications": mock_notifications}

@router.post("/subscribe")
async def subscribe_device(subscription: dict):
    """Save Web Push subscription object"""
    print(f"Device Subscribed: {subscription}")
    return {"status": "success", "message": "Device registered for push"}
