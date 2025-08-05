# app/utils/paystack_utils.py

import requests

def verify_paystack_transaction(reference):
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer YOUR_SECRET_KEY",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response_data['status'] and response_data['data']['status'] == 'success':
            return response_data['data']
        return None
    except Exception as e:
        print("Paystack verification error:", e)
        return None
