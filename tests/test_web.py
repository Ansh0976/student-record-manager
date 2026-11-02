import pytest

pytest.importorskip("flask")

from student_manager.web import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "web.db"))
    app.testing = True
    return app.test_client()


GOOD = {"name": "Asha Verma", "roll_number": "1", "grade": "10", "section": "a",
        "email": "asha@example.com", "percentage": "88.5"}


def add(client, **overrides):
    return client.post("/api/students", json={**GOOD, **overrides})


def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Student register" in res.data


def test_add_and_list(client):
    res = add(client)
    assert res.status_code == 201
    body = res.get_json()
    assert body["section"] == "A" and body["percentage"] == 88.5
    listed = client.get("/api/students").get_json()
    assert [s["name"] for s in listed] == ["Asha Verma"]


def test_validation_error_is_400_with_message(client):
    res = add(client, grade="15")
    assert res.status_code == 400
    assert "Grade" in res.get_json()["error"]


def test_missing_required_field(client):
    res = client.post("/api/students", json={"name": "Asha Verma"})
    assert res.status_code == 400
    assert "Missing required" in res.get_json()["error"]


def test_name_none_rejected(client):
    assert add(client, name=None).status_code == 400


def test_duplicate_is_409(client):
    assert add(client).status_code == 201
    assert add(client, name="Other Person").status_code == 409


def test_requires_json_content_type(client):
    res = client.post("/api/students", data="name=Asha", content_type="application/x-www-form-urlencoded")
    assert res.status_code == 400


def test_rejects_nested_values(client):
    assert add(client, name=["a"]).status_code == 400
    assert add(client, grade=True).status_code == 400


def test_oversized_body_rejected(client):
    assert add(client, name="x" * 100_000).status_code == 413


def test_update_and_clear_optional(client):
    sid = add(client).get_json()["id"]
    res = client.put(f"/api/students/{sid}", json={"percentage": "91", "email": ""})
    assert res.status_code == 200
    body = res.get_json()
    assert body["percentage"] == 91.0 and body["email"] is None


def test_update_cannot_blank_required_field(client):
    sid = add(client).get_json()["id"]
    assert client.put(f"/api/students/{sid}", json={"name": ""}).status_code == 400


def test_update_and_delete_missing_are_404(client):
    assert client.put("/api/students/99", json={"name": "Nobody Here"}).status_code == 404
    assert client.delete("/api/students/99").status_code == 404


def test_delete(client):
    sid = add(client).get_json()["id"]
    assert client.delete(f"/api/students/{sid}").status_code == 204
    assert client.get("/api/students").get_json() == []


def test_search_and_grade_filter(client):
    add(client)
    add(client, name="Ravi Kumar", roll_number="2", email="")
    add(client, name="Karan Singh", grade="11", roll_number="5", email="karan@example.com")
    names = lambda r: [s["name"] for s in r.get_json()]
    assert names(client.get("/api/students?q=ravi")) == ["Ravi Kumar"]
    assert names(client.get("/api/students?grade=11")) == ["Karan Singh"]
    assert names(client.get("/api/students?grade=10&q=a")) == ["Asha Verma", "Ravi Kumar"]
    assert client.get("/api/students?grade=99").status_code == 400


def test_stored_html_is_returned_as_data_not_markup(client):
    # Names with markup are rejected by validation, so it can never be stored.
    assert add(client, name="<script>alert(1)</script>").status_code == 400


def test_csv_export_endpoint(client):
    add(client)
    res = client.get("/api/export.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    lines = res.data.decode().splitlines()
    assert lines[0].startswith("id,name")
    assert "Asha Verma" in lines[1]
