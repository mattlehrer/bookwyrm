"""Implementation of the SealedDate class."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.forms import DateField
from django.forms.widgets import SelectDateWidget
from django.utils import timezone


_westmost_tz = timezone.get_fixed_timezone(timedelta(hours=-12))

# TODO: migrate SealedDate to `date`


class SealedDate(datetime):
    """a date object sealed into a certain precision (day, month, year)"""

    @property
    def has_day(self) -> bool:
        return self.has_month

    @property
    def has_month(self) -> bool:
        return True

    def partial_isoformat(self) -> str:
        return self.strftime("%Y-%m-%d")

    @classmethod
    def from_datetime(cls, dt) -> SealedDate:
        # pylint: disable=invalid-name
        return cls.combine(dt.date(), dt.time(), tzinfo=dt.tzinfo)

    @classmethod
    def from_date_parts(cls, year, month, day) -> SealedDate:
        # because SealedDate is actually a datetime object, we must create it with a
        # timezone such that its date remains stable no matter the values of USE_TZ,
        # current_timezone and default_timezone.
        return cls.from_datetime(datetime(year, month, day, tzinfo=_westmost_tz))


class MonthSeal(SealedDate):
    @property
    def has_day(self) -> bool:
        return False

    def partial_isoformat(self) -> str:
        return self.strftime("%Y-%m")


class YearSeal(SealedDate):
    @property
    def has_month(self) -> bool:
        return False

    def partial_isoformat(self) -> str:
        return self.strftime("%Y")


class SealedDateFormField(DateField):
    """date form field with support for SealedDate"""

    def prepare_value(self, value):
        # As a convention, Django's `SelectDateWidget` uses "0" for missing
        # parts. We piggy-back into that, to make it work with SealedDate.
        if not isinstance(value, SealedDate):
            return super().prepare_value(value)
        elif value.has_day:
            return value.strftime("%Y-%m-%d")
        elif value.has_month:
            return value.strftime("%Y-%m-0")
        else:
            return value.strftime("%Y-0-0")

    def to_python(self, value) -> SealedDate:
        try:
            date = super().to_python(value)
        except ValidationError as ex:
            if match := SelectDateWidget.date_re.match(value):
                year, month, day = map(int, match.groups())
            if not match or (day and not month) or not year:
                raise ex from None
            if not month:
                return YearSeal.from_date_parts(year, 1, 1)
            elif not day:
                return MonthSeal.from_date_parts(year, month, 1)
        else:
            if date is None:
                return None
            else:
                year, month, day = date.year, date.month, date.day

        return SealedDate.from_date_parts(year, month, day)
