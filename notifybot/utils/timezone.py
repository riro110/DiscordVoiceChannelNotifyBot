import datetime


def tz_localize(dt: datetime.datetime):
    # 記録上ではUTCだがプログラム上ではJSTで認識されてしまうため
    return dt + datetime.timedelta(hours=9)
