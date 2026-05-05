import azure.functions as func
import json
import logging
import datetime
import random
import config

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
    user = req.params.get("user", "default")

    otp = str(random.randint(1000, 9999))
    expiry = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=config.OTP_EXPIRY_MINUTES
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


@app.route(route="otps", auth_level=func.AuthLevel.ANONYMOUS)
def view_otps(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP Trigger: Retrieve all active OTPs.

    Returns:
        JSON response containing all OTPs with expiry timestamps.
    """
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


@app.timer_trigger(schedule=config.TIMER_SCHEDULE, arg_name="timer")
def cleanup_otps(timer: func.TimerRequest) -> None:
    """
    Timer Trigger: Cleanup expired OTPs.

    Runs on configured CRON schedule and removes OTPs
    whose expiry time has passed.
    """
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