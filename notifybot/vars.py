import dataclasses
import os
from datetime import tzinfo
from typing import Optional

import pytz
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')


@dataclasses.dataclass(frozen=True)
class Data:
    # timezone
    JST: tzinfo = pytz.timezone('Asia/Tokyo')

    # db
    DB_NAME: str = "voice-time.sqlite3"
    VC_HISTORY_TABLE_NAME: str = "vc_access_history"
    ACCESS_TIME_TABLE: str = "access_time"

    # token
    TOKEN: str = os.environ['TOKEN']

    # id
    NOTIFY_CHANNEL_ID: int = int(os.environ['NOTIFY_CHANNEL_ID'])
    SERVER_ID: int = int(os.environ['SERVER_ID'])

    # optional
    ERROR_NOTIFY_INCOMING_WEBHOOK_URL: Optional[str] = os.getenv(
        'ERROR_NOTIFY_INCOMING_WEBHOOK_URL')
