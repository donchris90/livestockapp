import os
import requests
from dotenv import load_dotenv
from app.models import User
from app import create_app, db

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

headers = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json"
}


def initiate_paystack_transfer(bank_code, account_number, amount, name):
    """
    Initiates a real payout via Paystack.
    :param bank_code: e.g., '058' (GTB)
    :param account_number: e.g., '0123456789'
    :param amount: in kobo (e.g., ₦1000 = 100000)
    :param name: Full name of recipient
    :return: dict with status and message/data
    """
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # 1. Create transfer recipient
    recipient_url = "https://api.paystack.co/transferrecipient"
    recipient_data = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }

    try:
        r = requests.post(recipient_url, json=recipient_data, headers=headers)
        res = r.json()
        if not res.get("status"):
            return {"status": False, "message": res.get("message", "Could not create recipient")}
        recipient_code = res["data"]["recipient_code"]
    except Exception as e:
        return {"status": False, "message": f"Recipient creation error: {str(e)}"}

    # 2. Make transfer
    transfer_url = "https://api.paystack.co/transfer"
    transfer_data = {
        "source": "balance",
        "amount": amount,
        "recipient": recipient_code,
        "reason": f"Payout to {name}"
    }

    try:
        r = requests.post(transfer_url, json=transfer_data, headers=headers)
        res = r.json()
        if res.get("status"):
            return {"status": True, "data": res["data"]}
        else:
            return {"status": False, "message": res.get("message", "Transfer failed")}
    except Exception as e:
        return {"status": False, "message": f"Transfer error: {str(e)}"}