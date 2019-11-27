import email
import datetime
import pytz


TIME_FORMAT = "%Y-%m-%d-%H:%M:%S-%Z"
TIMEZONE = None


def make_email_time_string(date_tuple):
    if date_tuple:
        receival_time_utc = email.utils.mktime_tz( date_tuple )
        local_date = datetime.datetime.fromtimestamp( receival_time_utc, tz=TIMEZONE )
        global time_format
        return local_date.strftime( TIME_FORMAT )
    else:
        return 'None'


def set_timezone(config_name):
    global TIMEZONE
    if config_name:
        TIMEZONE = pytz.timezone(config_name)
    else:
        TIMEZONE = None


def get_current_time_str():
    return datetime.datetime.now(TIMEZONE).strftime( TIME_FORMAT )


def convert_to_global_time(timestr):
    return datetime.datetime.strptime(timestr, TIME_FORMAT)
