import os
import sched
import time
import json
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from collections import namedtuple
from typing import Optional

from texttable import Texttable

WEEK_SECONDS = 604800
SCHEDULE_FILE = ".schedule.json"

EVENT_SEARCH_URL = "https://asvz.ch/asvz_api/event_search?format=json"
WEEKDAY_ID_MAP = {
    "Monday": 3999,
    "Tuesday": 4006,
    "Wednesday": 4007,
    "Thursday": 4002,
    "Friday": 4008,
    "Saturday": 4003,
    "Sunday": 4000,
}


class Event:
    def __init__(
        self,
        sport,
        weekday,
        start_time,
        facility,
        weekly=False,
        sign_up_start=None,
        sign_up_end=None,
        url=None,
    ):
        self.sport = sport
        self.weekday = weekday
        self.start_time = start_time
        self.facility = facility
        self.weekly = weekly
        self.sign_up_start = sign_up_start
        self.sign_up_end = sign_up_end
        self.url = url

    def __str__(self):
        return "\n".join(
            [
                f"Sport name: {self.sport}",
                f"Weekday: {self.weekday}",
                f"Start time: {self.start_time}",
                f"Facilty: {self.facility}",
                f"Weekly: {self.weekly}",
            ]
        )


class ScheduleManager:
    def __init__(self, driver=None):
        self.schedule = sched.scheduler(time.time)
        self.driver = driver
        self.load()

    def set_driver(self, driver):
        self.driver = driver

    def run(self):
        self.schedule.run()

    def schedule_next(self, event: Event):
        if event.weekly:
            new_event = event.get_next()
            if new_event:
                _, sign_up_time, url = get_event_info()
                self.schedule_event(new_event)

    def schedule_event(self, event: Event):
        self.schedule.enterabs(
            event.sign_up_start,
            1,
            self.execute,
            event,
        )

    def execute(self, event: Event):
        self.sign_up(event)
        self.schedule_next(event)

    def sign_up(self, schedule_event: Event):
        pass

    def find_event(self, sport, weekday, start_time, facility) -> Event:
        possible_weekdays = list(
            filter(
                lambda k: k.lower().startswith(weekday),
                WEEKDAY_ID_MAP.keys(),
            )
        )
        if len(possible_weekdays) == 1:
            weekday_id = WEEKDAY_ID_MAP[possible_weekdays[0]]
        elif len(possible_weekdays) > 1:
            raise ValueError(f"Ambiguous weekday {weekday}")
        else:
            raise ValueError(f"Unknown weekday {weekday}")

        parsed_start_time = datetime.strptime(start_time, "%H:%M")

        events_json = requests.get(
            EVENT_SEARCH_URL + f"&f[0]=weekday:{weekday_id}"
        ).json()["results"]

        for e in events_json:
            if (
                sport in e["sport_name"].lower()
                and facility in e["facility_name"][0].lower()
            ):
                e_parsed_start_time = datetime.fromisoformat(
                    e["from_date"].replace("Z", "+00:00")
                ).astimezone(ZoneInfo("Europe/Zurich"))
                if (
                    e_parsed_start_time.hour == parsed_start_time.hour
                    and e_parsed_start_time.minute == parsed_start_time.minute
                ):
                    found_event = e
                    break
        else:
            raise ValueError(f"Could not find event")

        event = Event(
            found_event["sport_name"],
            possible_weekdays[0],
            parsed_start_time.strftime("%H:%M"),
            e["facility_name"][0],
            sign_up_start=e["oe_from_date_stamp"],
            sign_up_end=e["to_date_stamp"],
            url=e["url"],
        )
        return event

    def add(self, sport, weekday, start_time, facility, weekly: bool = False):
        event = self.find_event(sport, weekday, start_time, facility)
        event.weekly = weekly

        self.schedule_event(event)
        self.store()

    def remove(self, event_id):
        if event_id < 0 or event_id > len(self.schedule.queue):
            print("Invalid ID")
        else:
            e = self.schedule.queue[event_id]
            self.schedule.cancel(e)
            self.store()
            print("The event was successfully removed")

    def store(self):
        with open(SCHEDULE_FILE, "w") as f:
            json.dump([e.argument.__dict__ for e in self.schedule.queue], f)

    def load(self):
        if os.path.isfile(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, "r") as f:
                for e in json.load(f):
                    self.schedule_event(Event(**e))

    def __str__(self):
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_align(["c", "c", "c", "c", "c", "c"])
        table.header(
            ["ID", "Sport", "Weekday", "Start time", "Facility", "Next signup time"]
        )

        for i, item in enumerate(self.schedule.queue):
            if type(item.argument) == Event:
                event = item.argument
                table.add_row(
                    [
                        i,
                        event.sport,
                        event.weekday,
                        event.start_time,
                        event.facility,
                        datetime.fromtimestamp(item.time).strftime("%a %m-%Y %H:%M"),
                    ]
                )

        return table.draw()
