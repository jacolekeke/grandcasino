import requests

test_api_key = "UgK3u/eHN6X8UrhwJRSIUT51rLrcJymTK6oHjwvYBlo="
test_api_password = "d_yTqtIfhn]g7V5A[v==Vp"


def authenticate(customer_id):
    r = requests.post("https://test.paygiga.com/api/transaction/authenticate", data={
        "merchantKey": test_api_key,
        "merchantPassword": test_api_password,
        "customerId": customer_id
    })
    return r.json()


def get_bank_list(customer_id, session_id):
    r = requests.post("https://test.paygiga.com/api/getBankList", data={
        "session_id": session_id,
        "aim": "deposit"
    })
    return r.json()


def get_available_amounts(customer_id, bank_code):
    session_id = authenticate(customer_id).get("session_id")
    banks = get_bank_list("1234", session_id).get("banks")[0].get("bankCode")

    r = requests.post("https://test.paygiga.com/api/getAvailableAmounts", data={
        "session_id": session_id, "minAmount": 10000, "maxAmount": 11000,
        "bankCode": banks, "customerId": customer_id, "approvalRowShowType": 2
    })
    return r.json()


def deposit_start(customer_id):
    session_id = authenticate(customer_id).get("session_id")
    banks = get_bank_list("1234", session_id).get("banks")[0].get("bankCode")
    r = requests.post("https://test.paygiga.com/api/deposit/start", data={
        "session_id": session_id, "id": 8, "description": "test", "customerId": "15",
        "customerName": "CUSTOMER NAME", "transactionId": "20", "bankCode": "isbank"
    })


print(get_available_amounts("1234", "akbank"))
