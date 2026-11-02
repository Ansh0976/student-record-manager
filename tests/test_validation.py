import pytest

from student_manager.validation import (
    ValidationError,
    validate_email,
    validate_grade,
    validate_name,
    validate_percentage,
    validate_roll_number,
    validate_section,
)


class TestName:
    def test_trims_and_collapses_spaces(self):
        assert validate_name("  Asha   Verma ") == "Asha Verma"

    @pytest.mark.parametrize("bad", ["", "A", "x" * 61, "Asha123", "Robert'); DROP", "a@b"])
    def test_rejects_bad_names(self, bad):
        with pytest.raises(ValidationError):
            validate_name(bad)

    def test_allows_apostrophe_hyphen_dot(self):
        assert validate_name("Mary-Ann O'Neil Jr.") == "Mary-Ann O'Neil Jr."


    def test_name_must_be_text(self):
        for bad in (None, 5, ["Asha"]):
            with pytest.raises(ValidationError):
                validate_name(bad)


class TestNumbers:
    def test_roll_number_ok(self):
        assert validate_roll_number(" 12 ") == 12

    @pytest.mark.parametrize("bad", ["0", "10000", "abc", "", "1.5"])
    def test_roll_number_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_roll_number(bad)

    @pytest.mark.parametrize("good", [1, "12", " 7 "])
    def test_grade_ok(self, good):
        assert validate_grade(good) == int(good)

    @pytest.mark.parametrize("bad", [0, 13, "x", ""])
    def test_grade_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_grade(bad)


class TestSection:
    def test_uppercases(self):
        assert validate_section(" b ") == "B"

    @pytest.mark.parametrize("bad", ["", "AB", "1", "é"])
    def test_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_section(bad)


class TestOptionalFields:
    @pytest.mark.parametrize("empty", [None, "", "   "])
    def test_empty_means_none(self, empty):
        assert validate_email(empty) is None
        assert validate_percentage(empty) is None

    def test_email_ok(self):
        assert validate_email("a@b.co") == "a@b.co"

    @pytest.mark.parametrize("bad", ["abc", "a@b", "a b@c.com", "@x.com"])
    def test_email_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_email(bad)

    def test_percentage_ok_and_rounding(self):
        assert validate_percentage("87.456") == 87.46
        assert validate_percentage("0") == 0.0
        assert validate_percentage(100) == 100.0

    @pytest.mark.parametrize("bad", ["-1", "100.1", "abc", "nan", "inf"])
    def test_percentage_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_percentage(bad)
