from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timedelta

from stock import db as dbm

# 市场收盘时间定义 (北京时间)
CN_CLOSE_HOUR = 15
# 美股收盘时间 (北京时间，保守估计，覆盖冬令时次日 05:00)
US_CLOSE_HOUR_CN_TIME = 6
# Crypto 日结时间 (北京时间，与美股对齐)
CRYPTO_CLOSE_HOUR_CN_TIME = 6


def check_data_availability(
    market: str, report_date: date_type | str, current_time: datetime | None = None
) -> bool:
    """
    检查指定市场在 report_date 的数据是否已经可用。
    基于北京时间判断。
    """
    if isinstance(report_date, str):
        report_date = date_type.fromisoformat(report_date)

    if current_time is None:
        current_time = datetime.now()

    # 如果是过去的时间，肯定可用
    if report_date < current_time.date():
        # 如果是昨天
        if report_date == current_time.date() - timedelta(days=1):
            # 检查是否已过收盘时间
            if market == dbm.ASSET_CLASS_CN:
                # 昨天 A 股收盘肯定过了
                return True
            elif market == dbm.ASSET_CLASS_US or market == dbm.ASSET_CLASS_CRYPTO:
                # 美股/Crypto 是次日收盘，所以如果是昨天的数据，今天收盘时间是今天早上
                return current_time.hour >= US_CLOSE_HOUR_CN_TIME
        else:
            # 前天及更早
            return True

    # 如果是今天
    if report_date == current_time.date():
        if market == dbm.ASSET_CLASS_CN:
            # A 股今天 15:30 后可用
            if current_time.hour > CN_CLOSE_HOUR:
                return True
            if current_time.hour == CN_CLOSE_HOUR and current_time.minute >= 30:
                return True
            return False
        elif market == dbm.ASSET_CLASS_US or market == dbm.ASSET_CLASS_CRYPTO:
            # 美股/Crypto 今天的数据要明天早上才出来
            return False

    # 如果是未来
    if report_date > current_time.date():
        return False

    return False
