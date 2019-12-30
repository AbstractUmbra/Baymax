""" Quick func to make a human readable timedelta. """

from datetime import (
    datetime
)
from dateutil.relativedelta import (
    relativedelta
)


__all__ = ('human_timedelta',)


def human_timedelta(dati: datetime):
    prefix = ''
    suffix = ''
    now = datetime.utcnow()
    now.replace(microsecond=0)
    dati.replace(microsecond=0)
    if now < dati:
        delta = relativedelta(dati, now)
        prefix = 'In '
    else:
        delta = relativedelta(now, dati)
        suffix = ' ago'
    output = []
    units = ('year', 'month', 'day', 'hour', 'minute', 'second')
    for unit in units:
        elem = getattr(delta, unit + 's')
        if not elem:
            continue
        if unit == 'day':
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                output.append('{} week{}'.format(
                    weeks, 's' if weeks > 1 else ''))
        output.append('{} {}{}'.format(elem, unit, 's' if elem > 1 else ''))
    output = output[:3]
    return prefix + ', '.join(output) + suffix
