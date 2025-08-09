import os
import datetime

CHAT_LOG_DIR = "logs/chat_log"

log_file = os.path.join(CHAT_LOG_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")

print(log_file)


log_file = log_file.split(".")[0] + "_" + str(1) + ".txt"

print(log_file)