import time
import json
import requests
from flask_mail import Mail, Message
from flask import current_app as app


def send_email(receiver_list, mail_subject, mail_body):
    try:
        app.logger.info(f'send_email called, receiver_list: {receiver_list}')
        msg = Message(
            subject=mail_subject,
            sender=app.config.get("MAIL_USERNAME"),
            recipients=receiver_list,
            body=mail_body
        )
        app.logger.info(f'msg created')
        app.logger.info(f'Send email now')
        mail = Mail(app)
        mail.send(msg)
        app.logger.info(f'Email sent')
    except Exception as e:
        app.logger.error(f'Exception occurred: {e}')
