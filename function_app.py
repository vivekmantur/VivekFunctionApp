import azure.functions as func
import json
import logging
import datetime
import os
import secrets

# ----------------------------------------
# Configuration and Constants
# ----------------------------------------

API_KEY = os.environ.get("API_KEY", "default-fallback")
OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "5"))
TIMER_SCHEDULE = os.environ.get("TIMER_SCHEDULE", "0 */5 * * *")

app = func.FunctionApp()

# In-memory OTP store
# Format: { "user": (otp, expiry_time) }
otp_store = {}


@app.route(route="generate-otp", auth_level=func.AuthLevel.ANONYMOUS)
def generate_otp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger: Generate OTP for a user.

    Query Params:
        user (str): Optional user identifier.

    Returns:
        JSON response containing OTP and expiry time.
    """
    try:
        user = req.params.get("user", "default")

        # Validate user input
        if not isinstance(user, str) or not user.strip():
            user = "default"

        # Secure OTP generation
        otp = str(secrets.SystemRandom().randint(1000, 9999))
        expiry = datetime.datetime.utcnow() + datetime.timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )

        otp_store[user] = (otp, expiry)
        logging.info("Generated OTP for user=%s", user)

        return func.HttpResponse(
            json.dumps(
                {
                    "user": user,
                    "otp": otp,
                    "expires_at": expiry.isoformat()
                }
            ),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error("Error generating OTP: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500
        )


@app.route(route="otps", auth_level=func.AuthLevel.FUNCTION)
def view_otps(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger: Retrieve all active OTPs.

    Requires function-level authentication.

    Returns:
        JSON response containing all OTPs with expiry timestamps.
    """
    try:
        data = {
            user: {
                "otp": otp,
                "expires_at": expiry.isoformat()
            }
            for user, (otp, expiry) in otp_store.items()
        }

        logging.info("Fetched %d OTP entries", len(data))
        return func.HttpResponse(
            json.dumps(data),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error("Error fetching OTPs: %s", str(e))
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500
        )


@app.timer_trigger(
    schedule=TIMER_SCHEDULE,
    arg_name="timer"
)
def cleanup_otps(timer: func.TimerRequest) -> None:
    """
    Timer Trigger: Cleanup expired OTPs.

    Runs on configured CRON schedule and removes OTPs
    whose expiry time has passed.
    """
    try:
        now = datetime.datetime.utcnow()
        expired_users = []

        for user, (otp, expiry) in otp_store.items():
            if expiry < now:
                expired_users.append(user)

        for user in expired_users:
            del otp_store[user]

        if expired_users:
            logging.info("Removed expired OTPs: %s", expired_users)
        else:
            logging.info("No expired OTPs found")
    except Exception as e:
        logging.error("Error cleaning up OTPs: %s", str(e))