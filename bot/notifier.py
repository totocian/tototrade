import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_trade_email(trade: dict) -> None:
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    recipient = os.getenv("ALERT_EMAIL", "ciancagliniantonio@gmail.com")

    if not smtp_user or not smtp_pass:
        logger.warning("Email not configured — set SMTP_USER and SMTP_PASS in .env")
        return

    action = trade.get("action", "")
    symbol = trade.get("symbol", "")
    score = trade.get("score", "")
    qty = trade.get("qty", "")
    price = trade.get("price", "")
    reason = trade.get("reason", "")

    if action == "BUY":
        subject = f"TotoTrade: BUY {symbol}"
        body = (
            f"BUY order placed\n\n"
            f"Symbol:  {symbol}\n"
            f"Qty:     {qty}\n"
            f"Price:   ${price}\n"
            f"Score:   {score}\n"
            f"Sector:  {trade.get('sector', 'N/A')}\n"
        )
    elif action == "SELL":
        subject = f"TotoTrade: SELL {symbol}"
        body = (
            f"SELL order placed\n\n"
            f"Symbol:  {symbol}\n"
            f"Score:   {score}\n"
            f"Reason:  {reason}\n"
        )
    else:
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        logger.info("Email sent: %s", subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
