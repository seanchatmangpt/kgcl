"""Sample data generator for KGC OS Graph Agent demonstration.

Generates realistic 24-hour activity patterns including:
- Application usage (deep work, collaboration, meetings)
- Browser navigation (research, communication, documentation)
- Calendar events (meetings, blocks, focus time)
- Natural context switches and work patterns
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


class ActivityGenerator:
    """Generate realistic synthetic activity data."""

    # Application usage patterns
    DEEP_WORK_APPS = [
        ("com.microsoft.VSCode", "Visual Studio Code"),
        ("com.jetbrains.pycharm", "PyCharm"),
        ("com.apple.dt.Xcode", "Xcode"),
        ("com.sublimetext.4", "Sublime Text"),
    ]

    COLLABORATION_APPS = [
        ("com.tinyspeck.slackmacgap", "Slack"),
        ("com.microsoft.teams", "Microsoft Teams"),
        ("us.zoom.xos", "Zoom"),
        ("com.apple.mail", "Mail"),
    ]

    RESEARCH_APPS = [
        ("com.apple.Safari", "Safari"),
        ("com.google.Chrome", "Chrome"),
        ("org.mozilla.firefox", "Firefox"),
    ]

    # Browser domains by category
    TECH_DOMAINS = [
        "github.com",
        "stackoverflow.com",
        "docs.python.org",
        "developer.mozilla.org",
        "aws.amazon.com",
    ]

    COMMUNICATION_DOMAINS = [
        "gmail.com",
        "mail.google.com",
        "outlook.com",
        "calendar.google.com",
    ]

    DOCUMENTATION_DOMAINS = [
        "readthedocs.io",
        "mkdocs.org",
        "sphinx-doc.org",
        "notion.so",
        "confluence.atlassian.com",
    ]

    def __init__(self, base_date: datetime | None = None) -> None:
        """Initialize activity generator.

        Parameters
        ----------
        base_date : datetime, optional
            Base date for activity generation (defaults to today)
        """
        self.base_date = base_date or datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.event_counter = 0

    def generate_day(
        self,
        day_offset: int = 0,
        include_weekend_pattern: bool = False,
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate a full day of activity.

        Parameters
        ----------
        day_offset : int
            Days to offset from base_date
        include_weekend_pattern : bool
            Use lighter weekend activity pattern

        Returns
        -------
        list[AppEvent | BrowserVisit | CalendarBlock]
            Generated events for the day
        """
        target_date = self.base_date + timedelta(days=day_offset)
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []

        if include_weekend_pattern:
            # Light weekend activity
            events.extend(self._generate_light_activity(target_date))
        else:
            # Full workday pattern
            events.extend(self._generate_morning_deep_work(target_date))
            events.extend(self._generate_late_morning_research(target_date))
            events.extend(self._generate_midday_meetings(target_date))
            events.extend(self._generate_afternoon_mixed(target_date))
            events.extend(self._generate_evening_wrapup(target_date))

        # Sort by timestamp
        return sorted(events, key=lambda e: e.timestamp)

    def generate_week(
        self, start_offset: int = 0
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate a full week of activity (7 days).

        Parameters
        ----------
        start_offset : int
            Days to offset the week start from base_date

        Returns
        -------
        list[AppEvent | BrowserVisit | CalendarBlock]
            Generated events for the week
        """
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []

        for day in range(7):
            is_weekend = (start_offset + day) % 7 in (5, 6)  # Saturday, Sunday
            events.extend(
                self.generate_day(
                    day_offset=start_offset + day,
                    include_weekend_pattern=is_weekend,
                )
            )

        return events

    def _generate_morning_deep_work(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate morning deep work period (8:00-11:00)."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []
        current_time = date.replace(hour=8, minute=0)

        # Extended focus session with minimal switches
        app_name, display_name = random.choice(self.DEEP_WORK_APPS)

        # Long coding session (2-3 hours)
        duration = random.uniform(7200, 10800)  # 2-3 hours
        events.append(
            AppEvent(
                event_id=self._next_id(),
                timestamp=current_time,
                app_name=app_name,
                app_display_name=display_name,
                window_title="main.py - kgcl",
                duration_seconds=duration,
                process_id=random.randint(1000, 9999),
            )
        )

        # Occasional documentation reference
        current_time += timedelta(seconds=duration)
        browser_app, browser_display = random.choice(self.RESEARCH_APPS)
        domain = random.choice(self.TECH_DOMAINS)

        events.append(
            BrowserVisit(
                event_id=self._next_id(),
                timestamp=current_time,
                url=f"https://{domain}/documentation/api",
                domain=domain,
                title="API Documentation",
                browser_name=browser_display,
                duration_seconds=random.uniform(120, 300),
                tab_id=f"tab_{uuid4().hex[:8]}",
            )
        )

        return events

    def _generate_late_morning_research(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate late morning research phase (11:00-12:00)."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []
        current_time = date.replace(hour=11, minute=0)

        # Frequent context switches during research
        browser_app, browser_display = random.choice(self.RESEARCH_APPS)

        # Multiple short browser visits
        for _ in range(random.randint(8, 15)):
            domain = random.choice(
                self.TECH_DOMAINS + self.DOCUMENTATION_DOMAINS
            )
            duration = random.uniform(60, 300)  # 1-5 minutes

            events.append(
                BrowserVisit(
                    event_id=self._next_id(),
                    timestamp=current_time,
                    url=f"https://{domain}/{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))}",
                    domain=domain,
                    title=f"Documentation - {domain}",
                    browser_name=browser_display,
                    duration_seconds=duration,
                    tab_id=f"tab_{uuid4().hex[:8]}",
                )
            )

            current_time += timedelta(seconds=duration + random.uniform(5, 20))

        # Check email/slack
        collab_app, collab_display = random.choice(self.COLLABORATION_APPS)
        events.append(
            AppEvent(
                event_id=self._next_id(),
                timestamp=current_time,
                app_name=collab_app,
                app_display_name=collab_display,
                window_title="General - Team Chat",
                duration_seconds=random.uniform(180, 420),
                process_id=random.randint(1000, 9999),
            )
        )

        return events

    def _generate_midday_meetings(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate midday meeting blocks (12:00-14:00)."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []

        # Lunch break (light activity)
        lunch_time = date.replace(hour=12, minute=0)

        # Daily standup
        standup_start = date.replace(hour=13, minute=0)
        standup_end = standup_start + timedelta(minutes=15)

        events.append(
            CalendarBlock(
                event_id=self._next_id(),
                timestamp=standup_start,
                end_time=standup_end,
                title="Daily Standup",
                description="Team sync meeting",
                location="Zoom",
                attendees=[f"team{i}@example.com" for i in range(1, 6)],
                organizer="manager@example.com",
                calendar_name="Work",
            )
        )

        # Zoom app during meeting
        events.append(
            AppEvent(
                event_id=self._next_id(),
                timestamp=standup_start,
                app_name="us.zoom.xos",
                app_display_name="Zoom",
                window_title="Daily Standup - Meeting",
                duration_seconds=900,  # 15 minutes
                process_id=random.randint(1000, 9999),
            )
        )

        # Project sync meeting
        if random.random() > 0.3:  # 70% chance
            sync_start = date.replace(hour=13, minute=30)
            sync_end = sync_start + timedelta(minutes=random.choice([30, 45, 60]))

            events.append(
                CalendarBlock(
                    event_id=self._next_id(),
                    timestamp=sync_start,
                    end_time=sync_end,
                    title="Project Sync",
                    description="Review progress and blockers",
                    location="Conference Room A",
                    attendees=[f"dev{i}@example.com" for i in range(1, 4)],
                    organizer="lead@example.com",
                    calendar_name="Work",
                )
            )

            events.append(
                AppEvent(
                    event_id=self._next_id(),
                    timestamp=sync_start,
                    app_name="com.microsoft.teams",
                    app_display_name="Microsoft Teams",
                    window_title="Project Sync",
                    duration_seconds=(sync_end - sync_start).total_seconds(),
                    process_id=random.randint(1000, 9999),
                )
            )

        return events

    def _generate_afternoon_mixed(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate afternoon mixed work (14:00-17:00)."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []
        current_time = date.replace(hour=14, minute=30)

        # Alternating between coding and collaboration
        for session in range(random.randint(3, 5)):
            if session % 2 == 0:
                # Coding session
                app_name, display_name = random.choice(self.DEEP_WORK_APPS)
                duration = random.uniform(1800, 3600)  # 30-60 minutes

                events.append(
                    AppEvent(
                        event_id=self._next_id(),
                        timestamp=current_time,
                        app_name=app_name,
                        app_display_name=display_name,
                        window_title=f"{'feature' if session == 0 else 'bugfix'}-{uuid4().hex[:8]}.py",
                        duration_seconds=duration,
                        process_id=random.randint(1000, 9999),
                    )
                )
            else:
                # Collaboration/communication
                collab_app, collab_display = random.choice(self.COLLABORATION_APPS)
                duration = random.uniform(300, 900)  # 5-15 minutes

                events.append(
                    AppEvent(
                        event_id=self._next_id(),
                        timestamp=current_time,
                        app_name=collab_app,
                        app_display_name=collab_display,
                        window_title="Thread Discussion",
                        duration_seconds=duration,
                        process_id=random.randint(1000, 9999),
                    )
                )

            current_time += timedelta(seconds=duration + random.uniform(30, 120))

        return events

    def _generate_evening_wrapup(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate evening wrap-up activities (17:00-18:00)."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []
        current_time = date.replace(hour=17, minute=0)

        # Email check
        events.append(
            AppEvent(
                event_id=self._next_id(),
                timestamp=current_time,
                app_name="com.apple.mail",
                app_display_name="Mail",
                window_title="Inbox",
                duration_seconds=random.uniform(300, 600),
                process_id=random.randint(1000, 9999),
            )
        )

        current_time += timedelta(minutes=10)

        # Documentation update
        browser_app, browser_display = random.choice(self.RESEARCH_APPS)
        domain = random.choice(self.DOCUMENTATION_DOMAINS)

        events.append(
            BrowserVisit(
                event_id=self._next_id(),
                timestamp=current_time,
                url=f"https://{domain}/project/kgcl/docs",
                domain=domain,
                title="Project Documentation",
                browser_name=browser_display,
                duration_seconds=random.uniform(600, 1200),
                tab_id=f"tab_{uuid4().hex[:8]}",
            )
        )

        # Planning for tomorrow
        current_time += timedelta(minutes=20)
        events.append(
            AppEvent(
                event_id=self._next_id(),
                timestamp=current_time,
                app_name="com.apple.Notes",
                app_display_name="Notes",
                window_title="Tomorrow's Tasks",
                duration_seconds=random.uniform(180, 360),
                process_id=random.randint(1000, 9999),
            )
        )

        return events

    def _generate_light_activity(
        self, date: datetime
    ) -> list[AppEvent | BrowserVisit | CalendarBlock]:
        """Generate light weekend activity pattern."""
        events: list[AppEvent | BrowserVisit | CalendarBlock] = []

        # Occasional check-in (morning)
        if random.random() > 0.5:
            morning_time = date.replace(hour=random.randint(9, 11), minute=0)

            # Quick email check
            events.append(
                AppEvent(
                    event_id=self._next_id(),
                    timestamp=morning_time,
                    app_name="com.apple.mail",
                    app_display_name="Mail",
                    window_title="Inbox",
                    duration_seconds=random.uniform(180, 420),
                    process_id=random.randint(1000, 9999),
                )
            )

            # Brief planning/note-taking
            events.append(
                AppEvent(
                    event_id=self._next_id(),
                    timestamp=morning_time + timedelta(minutes=10),
                    app_name="com.apple.Notes",
                    app_display_name="Notes",
                    window_title="Weekend Planning",
                    duration_seconds=random.uniform(300, 600),
                    process_id=random.randint(1000, 9999),
                )
            )

        return events

    def _next_id(self) -> str:
        """Generate next event ID."""
        self.event_counter += 1
        return f"evt_{self.event_counter:06d}"


def generate_sample_data(
    days: int = 7,
    start_date: datetime | None = None,
) -> list[AppEvent | BrowserVisit | CalendarBlock]:
    """Generate sample activity data for specified number of days.

    Parameters
    ----------
    days : int
        Number of days to generate (default: 7)
    start_date : datetime, optional
        Starting date (defaults to today)

    Returns
    -------
    list[AppEvent | BrowserVisit | CalendarBlock]
        Generated activity events
    """
    generator = ActivityGenerator(base_date=start_date)

    if days == 1:
        return generator.generate_day()
    else:
        return generator.generate_week(start_offset=0)


if __name__ == "__main__":
    # Demo: Generate and print sample data
    events = generate_sample_data(days=1)
    print(f"Generated {len(events)} events")
    print(f"\nEvent breakdown:")
    app_count = sum(1 for e in events if isinstance(e, AppEvent))
    browser_count = sum(1 for e in events if isinstance(e, BrowserVisit))
    cal_count = sum(1 for e in events if isinstance(e, CalendarBlock))
    print(f"  - AppEvents: {app_count}")
    print(f"  - BrowserVisits: {browser_count}")
    print(f"  - CalendarBlocks: {cal_count}")
