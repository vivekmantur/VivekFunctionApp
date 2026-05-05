import azure.functions as func
import json
import logging
import datetime
import random
import config

app = func.FunctionApp()

# In-memory OTP store
# { "user": (otp, expiry_time) }
otp_store = {}


# 🔹 Generate OTP
@app.route(route="generate-otp", auth_level=func.AuthLevel.ANONYMOUS)
def generate_otp(req: func.HttpRequest) -> func.HttpResponse:

    user = req.params.get("user", "default")

    otp = str(random.randint(1000, 9999))
    expiry = datetime.datetime.utcnow() + datetime.timedelta(
    minutes=config.OTP_EXPIRY_MINUTES
)

    otp_store[user] = (otp, expiry)

    logging.info(f"Generated OTP for {user}: {otp}")

    return func.HttpResponse(
        json.dumps({
            "user": user,
            "otp": otp,
            "expires_at": expiry.isoformat()
        }),
        mimetype="application/json"
    )


# 🔹 View OTPs (for testing)
@app.route(route="otps", auth_level=func.AuthLevel.ANONYMOUS)
def view_otps(req: func.HttpRequest) -> func.HttpResponse:

    data = {
        user: {
            "otp": otp,
            "expires_at": expiry.isoformat()
        }
        for user, (otp, expiry) in otp_store.items()
    }

    return func.HttpResponse(
        json.dumps(data),
        mimetype="application/json"
    )



# 🔹 Timer Trigger → Auto cleanup expired OTPs
@app.timer_trigger(schedule=config.TIMER_SCHEDULE, arg_name="timer")
def cleanup_otps(timer: func.TimerRequest):

    now = datetime.datetime.utcnow()
    expired_users = []

    for user, (otp, expiry) in otp_store.items():
        if expiry < now:
            expired_users.append(user)

    for user in expired_users:
        del otp_store[user]

    if expired_users:
        logging.info(f"Removed expired OTPs: {expired_users}")
    else:
        logging.info("No expired OTPs found")