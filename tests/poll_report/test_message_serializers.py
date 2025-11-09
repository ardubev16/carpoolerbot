import calendar
import datetime

from carpoolerbot.database.models import PollAnswer, TelegramUser
from carpoolerbot.poll_report.message_serializers import (
    _format_user_answer,
    _sorted_positive_answers,
    full_poll_result,
    whos_on_text,
)
from carpoolerbot.poll_report.types import ReturnTime


def create_poll_answer(
    user_id: int,
    user_fullname: str,
    poll_id: str = "test_poll",
    poll_option_id: int = 0,
    poll_answer: bool = True,
    override_answer: bool | None = None,
    driver_id: int | None = None,
    return_time: int = ReturnTime.AFTER_WORK,
) -> PollAnswer:
    """Create a PollAnswer object for testing."""
    # Create a real TelegramUser instance
    user = TelegramUser(user_id=user_id, user_fullname=user_fullname)

    # Create a real PollAnswer instance
    answer = PollAnswer(
        user_id=user_id,
        poll_id=poll_id,
        poll_option_id=poll_option_id,
        poll_answer=poll_answer,
        override_answer=override_answer,
        driver_id=driver_id,
        return_time=return_time,
    )
    # Set the user relationship manually (without database)
    answer.user = user

    return answer


class TestFormatUserAnswer:
    """Tests for _format_user_answer function."""

    def test_basic_user_no_special_flags(self) -> None:
        """Test formatting a user with no special flags."""
        answer = create_poll_answer(123, "John Doe")
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">John Doe</a>'

    def test_user_is_driver(self) -> None:
        """Test formatting when user is driving."""
        answer = create_poll_answer(123, "John Doe", driver_id=123)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">🚗 John Doe</a>'

    def test_user_goes_alone(self) -> None:
        """Test formatting when user goes alone."""
        answer = create_poll_answer(123, "John Doe", driver_id=-1)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">👤 John Doe</a>'

    def test_user_return_after_dinner(self) -> None:
        """Test formatting when user returns after dinner."""
        answer = create_poll_answer(123, "John Doe", return_time=ReturnTime.AFTER_DINNER)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">🍽 John Doe</a>'

    def test_user_return_late(self) -> None:
        """Test formatting when user returns late."""
        answer = create_poll_answer(123, "John Doe", return_time=ReturnTime.LATE)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">🎯 John Doe</a>'

    def test_driver_and_return_after_dinner(self) -> None:
        """Test formatting when user is driver and returns after dinner."""
        answer = create_poll_answer(123, "John Doe", driver_id=123, return_time=ReturnTime.AFTER_DINNER)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">🍽 🚗 John Doe</a>'

    def test_alone_and_return_late(self) -> None:
        """Test formatting when user goes alone and returns late."""
        answer = create_poll_answer(123, "John Doe", driver_id=-1, return_time=ReturnTime.LATE)
        result = _format_user_answer(answer)
        assert result == '<a href="tg://user?id=123">🎯 👤 John Doe</a>'


class TestSortedPositiveAnswers:
    """Tests for _sorted_positive_answers function."""

    def test_filters_positive_answers(self) -> None:
        """Test that only positive answers are returned."""
        answers = [
            create_poll_answer(1, "Alice", poll_answer=True),
            create_poll_answer(2, "Bob", poll_answer=False),
            create_poll_answer(3, "Charlie", poll_answer=True),
        ]
        result = _sorted_positive_answers(answers)
        assert len(result) == 2
        assert result[0].user.user_fullname == "Alice"
        assert result[1].user.user_fullname == "Charlie"

    def test_filters_out_override_false(self) -> None:
        """Test that override_answer=False filters out positive answers."""
        answers = [
            create_poll_answer(1, "Alice", poll_answer=True, override_answer=True),
            create_poll_answer(2, "Bob", poll_answer=True, override_answer=False),
            create_poll_answer(3, "Charlie", poll_answer=True),
        ]
        result = _sorted_positive_answers(answers)
        assert len(result) == 2
        assert result[0].user.user_fullname == "Alice"
        assert result[1].user.user_fullname == "Charlie"

    def test_sorts_by_fullname(self) -> None:
        """Test that results are sorted by user fullname (case-insensitive)."""
        answers = [
            create_poll_answer(1, "Zoe", poll_answer=True),
            create_poll_answer(2, "alice", poll_answer=True),
            create_poll_answer(3, "Bob", poll_answer=True),
        ]
        result = _sorted_positive_answers(answers)
        assert len(result) == 3
        assert result[0].user.user_fullname == "alice"
        assert result[1].user.user_fullname == "Bob"
        assert result[2].user.user_fullname == "Zoe"

    def test_empty_list(self) -> None:
        """Test with empty list."""
        result = _sorted_positive_answers([])
        assert result == []

    def test_all_negative_answers(self) -> None:
        """Test when all answers are negative."""
        answers = [
            create_poll_answer(1, "Alice", poll_answer=False),
            create_poll_answer(2, "Bob", poll_answer=False),
        ]
        result = _sorted_positive_answers(answers)
        assert result == []


class TestWhosOnText:
    """Tests for whos_on_text function."""

    def test_saturday(self) -> None:
        """Test output for Saturday."""
        saturday = datetime.datetime(2025, 11, 1)
        assert saturday.weekday() == calendar.SATURDAY

        answers = [create_poll_answer(1, "Alice")]
        result = whos_on_text(answers, saturday)
        assert result == "You are not working tomorrow, are you?"

    def test_sunday(self) -> None:
        """Test output for Sunday."""
        sunday = datetime.datetime(2025, 11, 2)
        assert sunday.weekday() == calendar.SUNDAY

        answers = [create_poll_answer(1, "Alice")]
        result = whos_on_text(answers, sunday)
        assert result == "You are not working tomorrow, are you?"

    def test_no_one_going(self) -> None:
        """Test when no one is going to the office."""
        monday = datetime.datetime(2025, 11, 3)
        assert monday.weekday() == calendar.MONDAY

        answers = [
            create_poll_answer(1, "Alice", poll_answer=False),
            create_poll_answer(2, "Bob", poll_answer=False),
        ]
        result = whos_on_text(answers, monday)
        assert result == "Nobody is going on site on <b>Monday</b>."

    def test_single_person_going(self) -> None:
        """Test when one person is going."""
        monday = datetime.datetime(2025, 11, 3)
        assert monday.weekday() == calendar.MONDAY

        answers = [create_poll_answer(1, "Alice")]
        result = whos_on_text(answers, monday)

        assert "On <b>Monday</b> is going on site:" in result
        assert '<a href="tg://user?id=1">Alice</a>' in result

    def test_multiple_people_going(self) -> None:
        """Test when multiple people are going."""
        monday = datetime.datetime(2025, 11, 3)
        assert monday.weekday() == calendar.MONDAY

        answers = [
            create_poll_answer(1, "Charlie", poll_answer=True),
            create_poll_answer(2, "Alice", poll_answer=True),
            create_poll_answer(3, "Bob", poll_answer=True),
        ]
        result = whos_on_text(answers, monday)

        assert "On <b>Monday</b> is going on site:" in result
        # Check that users are sorted alphabetically
        lines = result.split("\n")
        assert '<a href="tg://user?id=2">Alice</a>' in lines[2]
        assert '<a href="tg://user?id=3">Bob</a>' in lines[3]
        assert '<a href="tg://user?id=1">Charlie</a>' in lines[4]

    def test_people_with_different_flags(self) -> None:
        """Test output with users having different driver/return time flags."""
        monday = datetime.datetime(2025, 11, 3)
        assert monday.weekday() == calendar.MONDAY

        answers = [
            create_poll_answer(1, "Alice", driver_id=1),
            create_poll_answer(2, "Bob", driver_id=-1),
            create_poll_answer(3, "Charlie", return_time=ReturnTime.LATE),
        ]
        result = whos_on_text(answers, monday)

        assert "On <b>Monday</b> is going on site:" in result
        assert "🚗 Alice" in result
        assert "👤 Bob" in result
        assert "🎯 Charlie" in result

    def test_user_multiple_answers(self) -> None:
        """Test when a user has multiple answers (only positive counted)."""
        monday = datetime.datetime(2025, 11, 3)
        assert monday.weekday() == calendar.MONDAY

        answers = [
            create_poll_answer(1, "Alice", poll_option_id=0, poll_answer=True),
            create_poll_answer(1, "Alice", poll_option_id=1, poll_answer=True),
        ]
        result = whos_on_text(answers, monday)

        assert result.count("Alice") == 1


class TestFullPollResult:
    """Tests for full_poll_result function."""

    def test_empty_list(self) -> None:
        """Test with empty poll answers list."""
        result = full_poll_result([])
        assert result == ""

    def test_single_day_single_person(self) -> None:
        """Test with one person voting for one day."""
        answers = [create_poll_answer(1, "Alice", poll_option_id=0)]  # Monday
        result = full_poll_result(answers)

        assert "<b>Monday</b>:" in result
        assert '<a href="tg://user?id=1">Alice</a>' in result

    def test_multiple_days(self) -> None:
        """Test with people voting for multiple days."""
        answers = [
            create_poll_answer(1, "Alice", poll_option_id=0),  # Monday
            create_poll_answer(2, "Bob", poll_option_id=1),  # Tuesday
            create_poll_answer(3, "Charlie", poll_option_id=2),  # Wednesday
        ]
        result = full_poll_result(answers)

        assert "<b>Monday</b>:" in result
        assert "<b>Tuesday</b>:" in result
        assert "<b>Wednesday</b>:" in result
        assert '<a href="tg://user?id=1">Alice</a>' in result
        assert '<a href="tg://user?id=2">Bob</a>' in result
        assert '<a href="tg://user?id=3">Charlie</a>' in result

    def test_multiple_people_same_day(self) -> None:
        """Test with multiple people voting for the same day."""
        answers = [
            create_poll_answer(1, "Charlie", poll_option_id=0),
            create_poll_answer(2, "Alice", poll_option_id=0),
            create_poll_answer(3, "Bob", poll_option_id=0),
        ]
        result = full_poll_result(answers)

        lines = result.split("\n")
        assert "<b>Monday</b>:" in lines[0]
        # Check alphabetical ordering
        assert "Alice" in lines[1]
        assert "Bob" in lines[2]
        assert "Charlie" in lines[3]

    def test_filters_negative_answers(self) -> None:
        """Test that negative answers are filtered out."""
        answers = [
            create_poll_answer(1, "Alice", poll_option_id=0, poll_answer=True),
            create_poll_answer(2, "Bob", poll_option_id=0, poll_answer=False),
        ]
        result = full_poll_result(answers)

        assert "Alice" in result
        assert "Bob" not in result

    def test_filters_override_false(self) -> None:
        """Test that override_answer=False filters out answers."""
        answers = [
            create_poll_answer(1, "Alice", poll_option_id=0, poll_answer=True),
            create_poll_answer(2, "Bob", poll_option_id=0, poll_answer=True, override_answer=False),
        ]
        result = full_poll_result(answers)

        assert "Alice" in result
        assert "Bob" not in result

    def test_complex_week_schedule(self) -> None:
        """Test a complex week schedule with multiple days and people."""
        answers = [
            # Monday
            create_poll_answer(1, "Alice", poll_option_id=0, driver_id=1),
            create_poll_answer(2, "Bob", poll_option_id=0),
            # Tuesday
            create_poll_answer(1, "Alice", poll_option_id=1, poll_answer=False),
            create_poll_answer(2, "Bob", poll_option_id=1, driver_id=-1),
            # Wednesday
            create_poll_answer(1, "Alice", poll_option_id=2, return_time=ReturnTime.LATE),
            create_poll_answer(2, "Bob", poll_option_id=2, poll_answer=False),
        ]
        result = full_poll_result(answers)

        # Verify structure
        assert "<b>Monday</b>:" in result
        assert "<b>Tuesday</b>:" in result
        assert "<b>Wednesday</b>:" in result

        # Verify Monday has both Alice (driver) and Bob
        monday_section = result.split("<b>Tuesday</b>:")[0]
        assert "🚗 Alice" in monday_section
        assert "Bob" in monday_section

        # Verify Tuesday has only Bob (alone)
        tuesday_section = result.split("<b>Tuesday</b>:")[1].split("<b>Wednesday</b>:")[0]
        assert "👤 Bob" in tuesday_section
        assert "Alice" not in tuesday_section

        # Verify Wednesday has only Alice (late return)
        wednesday_section = result.split("<b>Wednesday</b>:")[1]
        assert "🎯 Alice" in wednesday_section
        assert "Bob" not in wednesday_section
