"""Send one test email to SMTP_USER, using the same TLS/login settings as reminders."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import smtplib
import ssl
from email.message import EmailMessage
from app.cli import smtp_password

if __name__ == '__main__':
    message = EmailMessage()
    message['From'] = os.environ['SMTP_FROM']
    message['To'] = os.environ['SMTP_USER']
    message['Subject'] = 'Kiểm tra email Thư viện số'
    message.set_content('Hệ thống Thư viện số đã gửi email thử thành công.')
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', '587')), timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(os.environ['SMTP_USER'], smtp_password(), initial_response_ok=False)
        smtp.send_message(message)
    print('SMTP đã chấp nhận email thử. Kiểm tra hộp thư đến và thư rác.')
