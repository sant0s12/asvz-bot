import logging
import argparse
from login import LoginManager
from schedule import ScheduleManager
from datetime import timedelta

logging.basicConfig(format="[%(name)s] %(levelname)s: %(message)s", level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=False, dest="command")

    parser_add = subparsers.add_parser("add", help="add new event")
    parser_add.add_argument("sport", action="store", help="sport name")
    parser_add.add_argument("weekday", action="store", help="weekday")
    parser_add.add_argument(
        "start_time", action="store", metavar="start-time", help="start time"
    )
    parser_add.add_argument(
        "--weekly",
        "-w",
        action="store_true",
        help="sign up to this event every week",
    )
    parser_add.add_argument("facility", action="store", help="facility")

    parser_remove = subparsers.add_parser("remove", help="remove event")
    parser_remove.add_argument(
        "id", type=int, action="store", help="id of event to be removed"
    )

    parser_show = subparsers.add_parser("show", help="show current schedule")

    parser_run = subparsers.add_parser("run", help="run the scheduler")

    return parser.parse_args()


def main():
    args = parse_args()

    schedule = ScheduleManager()

    if not args.command or args.command == "show":
        print(schedule)
    elif args.command == "remove":
        schedule.remove(args.id)
    elif args.command == "add":
        schedule.add(
            args.sport, args.weekday, args.start_time, args.facility, args.weekly
        )
    elif args.command == "run":
        driver = LoginManager().get_driver()

        schedule.set_driver(driver)
        schedule.run()


if __name__ == "__main__":
    main()
