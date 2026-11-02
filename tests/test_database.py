import pytest

from student_manager.database import (
    DuplicateStudentError,
    StudentNotFoundError,
    StudentRepository,
)
from student_manager.validation import ValidationError


@pytest.fixture
def repo():
    with StudentRepository(":memory:") as r:
        yield r


def seed(repo):
    repo.add("Asha Verma", 1, 10, "A", "asha@example.com", 88.5)
    repo.add("Ravi Kumar", 2, 10, "A", None, 72)
    repo.add("Meera Joshi", 1, 10, "B")
    repo.add("Karan Singh", 5, 11, "A", "karan@example.com")


def test_add_and_get(repo):
    s = repo.add("Asha Verma", "1", "10", "a", "asha@example.com", "88.5")
    assert (s.name, s.roll_number, s.grade, s.section) == ("Asha Verma", 1, 10, "A")
    assert s.percentage == 88.5
    assert repo.get(s.id) == s


def test_add_rejects_invalid_input(repo):
    with pytest.raises(ValidationError):
        repo.add("A", 1, 10, "A")
    assert repo.count() == 0


def test_duplicate_roll_in_same_class_rejected(repo):
    repo.add("Asha Verma", 1, 10, "A")
    with pytest.raises(DuplicateStudentError):
        repo.add("Someone Else", 1, 10, "A")
    assert repo.count() == 1


def test_same_roll_allowed_in_different_section(repo):
    repo.add("Asha Verma", 1, 10, "A")
    repo.add("Meera Joshi", 1, 10, "B")
    assert repo.count() == 2


def test_list_ordering_and_filters(repo):
    seed(repo)
    assert [s.name for s in repo.list_all()] == [
        "Asha Verma", "Ravi Kumar", "Meera Joshi", "Karan Singh",
    ]
    assert len(repo.list_all(grade=10)) == 3
    assert [s.name for s in repo.list_all(grade=10, section="b")] == ["Meera Joshi"]


def test_search_name_and_email_case_insensitive(repo):
    seed(repo)
    assert [s.name for s in repo.search("ASHA")] == ["Asha Verma"]
    assert [s.name for s in repo.search("karan@")] == ["Karan Singh"]
    assert repo.search("nobody") == []


def test_search_treats_wildcards_literally(repo):
    seed(repo)
    assert repo.search("%") == []
    assert repo.search("_") == []


def test_sql_injection_text_is_just_text(repo):
    seed(repo)
    assert repo.search("' OR '1'='1") == []
    assert repo.count() == 4


def test_update_changes_only_given_fields(repo):
    s = repo.add("Asha Verma", 1, 10, "A", "asha@example.com", 80)
    updated = repo.update(s.id, percentage="91.2", name="Asha V. Verma")
    assert updated.percentage == 91.2
    assert updated.name == "Asha V. Verma"
    assert updated.email == "asha@example.com"


def test_update_can_clear_optional_field(repo):
    s = repo.add("Asha Verma", 1, 10, "A", "asha@example.com")
    assert repo.update(s.id, email="").email is None


def test_update_validation_and_unknown_field(repo):
    s = repo.add("Asha Verma", 1, 10, "A")
    with pytest.raises(ValidationError):
        repo.update(s.id, grade=99)
    with pytest.raises(ValueError):
        repo.update(s.id, id=500)
    with pytest.raises(ValueError):
        repo.update(s.id)
    assert repo.get(s.id).grade == 10


def test_update_duplicate_rejected(repo):
    repo.add("Asha Verma", 1, 10, "A")
    b = repo.add("Ravi Kumar", 2, 10, "A")
    with pytest.raises(DuplicateStudentError):
        repo.update(b.id, roll_number=1)
    assert repo.get(b.id).roll_number == 2


def test_update_and_delete_missing(repo):
    with pytest.raises(StudentNotFoundError):
        repo.update(42, name="Nobody Here")
    with pytest.raises(StudentNotFoundError):
        repo.delete(42)


def test_delete(repo):
    s = repo.add("Asha Verma", 1, 10, "A")
    repo.delete(s.id)
    assert repo.count() == 0
    with pytest.raises(StudentNotFoundError):
        repo.get(s.id)


def test_data_persists_on_disk(tmp_path):
    db = str(tmp_path / "s.db")
    with StudentRepository(db) as r:
        r.add("Asha Verma", 1, 10, "A")
    with StudentRepository(db) as r:
        assert r.count() == 1
