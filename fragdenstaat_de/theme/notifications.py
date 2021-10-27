from django.conf import settings

import requests


def send_notification(message):
    return send_notification_slack(message)


def send_notification_slack(message):
    if not settings.SLACK_WEBHOOK_URL:
        return

    channel = settings.SLACK_DEFAULT_CHANNEL

    requests.post(
        settings.SLACK_WEBHOOK_URL,
        json={
            "channel": channel,
            "username": "fds-notification-bot",
            "text": message,
            "icon_emoji": ":money_with_wings:",
        },
    )
