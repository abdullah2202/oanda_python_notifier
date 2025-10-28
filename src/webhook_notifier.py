import requests
import os
import json

class WebhookNotifier:
    def __init__(self):
        self.url = os.getenv("WEBHOOK_URL")
        if not self.url:
            print("WARNING: WEBHOOK_URL not set. Notifications will be printed to console.")

    def send_notification(self, payload):
        if not self.url:
            print(f"Webhook Payload (Not Sent): {json.dumps(payload, indent=2)}")
            return

        try:
            response = requests.post(self.url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()  # Raise an exception for bad status codes
            print(f"Successfully sent webhook: {payload.get('strategy')}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending webhook: {e}")