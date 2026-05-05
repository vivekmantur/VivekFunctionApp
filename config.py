import os

# OTP expiry in minutes (default = 1)
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "1"))

# Timer schedule (default = every 10 seconds)
TIMER_SCHEDULE = os.getenv("TIMER_SCHEDULE", "*/10 * * * * *")