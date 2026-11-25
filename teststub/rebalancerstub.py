
from flask import Flask, request, jsonify
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

app = Flask(__name__)


# --------------------------------------------------
# SIMULATED OAUTH TOKEN REGISTRY
# --------------------------------------------------

# In a real OAuth implementation, tokens would be issued
# and validated by an authorisation server.
#
# For this assessment stub, we simulate that behaviour
# using an in-memory dictionary.

TOKENS = {
    "valid-token": {
        "user_id": "USER001",
        "active": True,
        "accounts": {
            "ACC001": ["read", "rebalance"],
            "ACC002": ["read"]
        }
    },

    "user-two-token": {
        "user_id": "USER002",
        "active": True,
        "accounts": {
            "ACC002": ["read", "rebalance"]
        }
    },

    "viewer-token": {
        "user_id": "USER003",
        "active": True,
        "accounts": {
            "ACC003": ["read"]
        }
    },

    "expired-token": {
        "user_id": "USER001",
        "active": False,
        "accounts": {
            "ACC001": ["read", "rebalance"]
        }
    }
}

accounts = {
    "ACC001": {
        "total_assets": Decimal("100000.00"),
        "currency": "USD",
        "securities": [
            {
                "symbol": "AAPL",
                "variance": "-5.00",
                "price": "200.00"
            },
            {
                "symbol": "MSFT",
                "variance": "3.00",
                "price": "400.00"
            },
            {
                "symbol": "GOOGL",
                "variance": "2.00",
                "price": "180.00"
            }
        ]
    },
    "ACC002": {
            "total_assets": Decimal("100000.00"),
            "currency": "GBP",
            "securities": [
                {
                    "symbol": "AAPL",
                    "variance": "-5.00",
                    "price": "200.00"
                },
                {
                    "symbol": "MSFT",
                    "variance": "3.00",
                    "price": "400.00"
                },
                {
                    "symbol": "GOOGL",
                    "variance": "2.00",
                    "price": "180.00"
                }
            ]
        }
}

# --------------------------------------------------
# AUTHENTICATION AND AUTHORISATION
# --------------------------------------------------

def authenticate(required_permission):
    """
    Validates the bearer token and checks whether
    the authenticated user has permission to access
    the requested account.
    """

    def decorator(f):

        @wraps(f)
        def decorated_function(account_number, *args, **kwargs):

            # Retrieve the authentication header.
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({
                    "error": "Missing or invalid authentication header"
                }), 401

            # Extract the bearer token.
            token = auth_header.split(" ", 1)[1]

            # Validate the token.
            user = TOKENS.get(token)

            if user is None:
                return jsonify({
                    "error": "Invalid authentication token"
                }), 401

            # Check whether the token has expired.
            if not user["active"]:
                return jsonify({
                    "error": "Authentication token expired"
                }), 401

            # Check whether the user can access this account.
            account_permissions = user["accounts"].get(account_number)

            if account_permissions is None:
                return jsonify({
                    "error": "Account access denied"
                }), 403

            
            # Check whether the user has the required permission.
            if required_permission not in account_permissions:
                return jsonify({
                    "error": "Insufficient permissions"
                }), 403

            # Pass the authenticated identity to the endpoint.
            return f(
                account_number,
                authenticated_user=user["user_id"],
                *args,
                **kwargs
            )

        return decorated_function

    return decorator


# --------------------------------------------------
# ACCOUNT REBALANCING ENDPOINT
# --------------------------------------------------

@app.route("/accounts/<account_number>/rebalance", methods=["POST"])
@authenticate("rebalance")
def rebalance(account_number, authenticated_user):

    # Retrieve account information from the internal account store.
    account = accounts.get(account_number)

    if account is None:
        return jsonify({
            "error": "Account not found"
        }), 404

    # Retrieve total assets from the account record.
    total_assets = account["total_assets"]

    # Securities are supplied as part of the rebalance instruction.
    data = request.get_json()

    securities = data["securities"]

    trades = []

    for security in securities:

        variance = Decimal(str(security["variance"]))
        price = Decimal(str(security["price"]))

        trade_value = abs(total_assets * variance / Decimal("100"))

        if price <= 0:
            return jsonify({
                "error": f"Invalid price for {security['symbol']}"
            }), 400

        shares = (trade_value / price).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if variance < 0:
            action = "BUY"
        elif variance > 0:
            action = "SELL"
        else:
            action = "HOLD"

        actual_trade_value = shares * price

        trades.append({
            "symbol": security["symbol"],
            "action": action,
            "shares": str(shares),
            "trade_value": str(actual_trade_value.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            ))
        })

    return jsonify({
        "account_number": account_number,
        "authenticated_user": authenticated_user,
        "total_assets": str(total_assets),
        "currency": account["currency"],
        "trades": trades
    })

if __name__ == "__main__":
    app.run(debug=True)