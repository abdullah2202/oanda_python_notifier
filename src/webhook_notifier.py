import requests
import os
import json
import urllib.parse

class WebhookNotifier:
    def __init__(self, parse_mode="Markdown"):
        """
        parse_mode: "Markdown", "HTML", or None
        """
        self.url = os.getenv("WEBHOOK_URL")  # Should include bot token + /sendMessage
        self.parse_mode = parse_mode

        if not self.url:
            print("WARNING: WEBHOOK_URL not set. Notifications will be printed to console.")

    def send_notification(self, payload, keyboard_buttons=None):
        """
        payload: dict containing fields like strategy, instrument, etc.
        keyboard_buttons: optional list of lists of dicts
            Example:
            [
                [{"text": "Open Chart", "url": "https://tradingview.com/..."}],
                [{"text": "Acknowledge", "callback_data": "ack"}]
            ]
        """

        # Build formatted message (supports Markdown or HTML depending on parse_mode)
        if self.parse_mode == "HTML":
            message_content = (
                f"<b>STRATEGY ALERT: {payload.get('strategy')}</b>\n"
                f"<b>Instrument:</b> {payload.get('instrument')}\n"
                f"<b>Timeframe:</b> {payload.get('timeframe')}\n"
                f"<b>Candle Time:</b> {payload.get('candle_time')}\n"
                f"<b>Setup:</b> {payload.get('message')}"
            )
        else:  # Markdown (default)
            message_content = (
                f"*STRATEGY ALERT: {payload.get('strategy')}*\n"
                f"*Instrument:* {payload.get('instrument')}\n"
                f"*Timeframe:* {payload.get('timeframe')}\n"
                f"*Candle Time:* {payload.get('candle_time')}\n"
                f"*Setup:* {payload.get('message')}"
            )

        # If no webhook URL, print instead of sending
        if not self.url:
            print("Telegram Payload (Not Sent):")
            print(message_content)
            if keyboard_buttons:
                print("Keyboard:", json.dumps(keyboard_buttons, indent=2))
            return

        # Telegram expects POST JSON payload
        telegram_payload = {
            "text": message_content,
            "parse_mode": self.parse_mode,
        }

        # Add inline keyboard if provided
        if keyboard_buttons:
            telegram_payload["reply_markup"] = {
                "inline_keyboard": keyboard_buttons
            }

        try:
            response = requests.post(
                self.url,
                json=telegram_payload
            )
            response.raise_for_status()
            print(f"Successfully sent Telegram alert: {payload.get('strategy')}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending Telegram message: {e}")
