import pytest
# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────
def make_user(client, name="Alice", email="alice@test.com", phone=""):
    r = client.post("/users", json={"name": name, "email": email, "phone": phone})
    assert r.status_code == 201, r.text
    return r.json()
def make_category(client, name="Food", description=""):
    r = client.post("/categories", json={"name": name, "description": description})
    assert r.status_code == 201, r.text
    return r.json()
def make_expense(client, user_id, category_id, **kwargs):
    payload = {
        "title":  "Lunch",
        "amount": 15.0,
        "date":   "2025-03-10",
        "user_id":     user_id,
        "category_id": category_id,
        **kwargs,
    }
    r = client.post("/expenses", json=payload)
    assert r.status_code == 201, r.text
    return r.json()
# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
# ══════════════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════════════
def test_create_user(client):
    u = make_user(client)
    assert u["name"]  == "Alice"
    assert u["email"] == "alice@test.com"
    assert "id" in u
def test_create_user_with_phone(client):
    u = make_user(client, phone="+1-555-0100")
    assert u["phone"] == "+1-555-0100"
def test_duplicate_email_rejected(client):
    make_user(client)
    r = client.post("/users", json={"name": "Bob", "email": "alice@test.com"})
    assert r.status_code == 400
def test_list_users(client):
    make_user(client, "Alice", "alice@test.com")
    make_user(client, "Bob",   "bob@test.com")
    r = client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) == 2
def test_get_user(client):
    u = make_user(client)
    r = client.get(f"/users/{u['id']}")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@test.com"
def test_get_user_not_found(client):
    r = client.get("/users/9999")
    assert r.status_code == 404
def test_update_user(client):
    u = make_user(client)
    r = client.put(f"/users/{u['id']}", json={"name": "Alice Smith"})
    assert r.status_code == 200
    assert r.json()["name"] == "Alice Smith"
def test_update_user_duplicate_email(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")
    r  = client.put(f"/users/{u2['id']}", json={"email": "alice@test.com"})
    assert r.status_code == 400
def test_delete_user(client):
    u = make_user(client)
    r = client.delete(f"/users/{u['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/users/{u['id']}")
    assert r2.status_code == 404
def test_delete_user_cascades_expenses(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"])
    client.delete(f"/users/{u['id']}")
    r = client.get("/expenses", params={"user_id": u["id"]})
    assert r.json() == []
# ══════════════════════════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════
def test_create_category(client):
    c = make_category(client, "Transport", "Bus and trains")
    assert c["name"]        == "Transport"
    assert c["description"] == "Bus and trains"
def test_duplicate_category_rejected(client):
    make_category(client)
    r = client.post("/categories", json={"name": "Food"})
    assert r.status_code == 400
def test_list_categories(client):
    make_category(client, "Food")
    make_category(client, "Rent")
    r = client.get("/categories")
    assert len(r.json()) == 2
def test_update_category(client):
    c = make_category(client)
    r = client.put(f"/categories/{c['id']}", json={"description": "All meals"})
    assert r.json()["description"] == "All meals"
def test_delete_category(client):
    c = make_category(client)
    r = client.delete(f"/categories/{c['id']}")
    assert r.status_code == 204
def test_delete_category_in_use_blocked(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"])
    r = client.delete(f"/categories/{c['id']}")
    assert r.status_code == 400
# ══════════════════════════════════════════════════════════════════════════════
#  EXPENSES
# ══════════════════════════════════════════════════════════════════════════════
def test_create_expense(client):
    u = make_user(client)
    c = make_category(client)
    e = make_expense(client, u["id"], c["id"], amount=42.5, notes="Team lunch")
    assert e["amount"] == 42.5
    assert e["notes"]  == "Team lunch"
def test_expense_amount_zero_rejected(client):
    u = make_user(client)
    c = make_category(client)
    r = client.post("/expenses", json={
        "title": "Bad", "amount": 0, "date": "2025-01-01",
        "user_id": u["id"], "category_id": c["id"],
    })
    assert r.status_code == 422
def test_expense_negative_amount_rejected(client):
    u = make_user(client)
    c = make_category(client)
    r = client.post("/expenses", json={
        "title": "Bad", "amount": -10, "date": "2025-01-01",
        "user_id": u["id"], "category_id": c["id"],
    })
    assert r.status_code == 422
def test_expense_invalid_user(client):
    c = make_category(client)
    r = client.post("/expenses", json={
        "title": "X", "amount": 5, "date": "2025-01-01",
        "user_id": 9999, "category_id": c["id"],
    })
    assert r.status_code == 404
def test_expense_invalid_category(client):
    u = make_user(client)
    r = client.post("/expenses", json={
        "title": "X", "amount": 5, "date": "2025-01-01",
        "user_id": u["id"], "category_id": 9999,
    })
    assert r.status_code == 404
def test_list_expenses_filtered(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")
    c  = make_category(client)
    make_expense(client, u1["id"], c["id"])
    make_expense(client, u2["id"], c["id"])
    r = client.get("/expenses", params={"user_id": u1["id"]})
    data = r.json()
    assert len(data) == 1
    assert data[0]["user_id"] == u1["id"]
def test_get_expense(client):
    u = make_user(client)
    c = make_category(client)
    e = make_expense(client, u["id"], c["id"])
    r = client.get(f"/expenses/{e['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == e["id"]
def test_update_expense(client):
    u = make_user(client)
    c = make_category(client)
    e = make_expense(client, u["id"], c["id"])
    r = client.put(f"/expenses/{e['id']}", json={"amount": 99.99, "title": "Updated"})
    assert r.json()["amount"] == 99.99
    assert r.json()["title"]  == "Updated"
def test_reassign_expense_to_another_user(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")
    c  = make_category(client)
    e  = make_expense(client, u1["id"], c["id"])
    r  = client.put(f"/expenses/{e['id']}", json={"user_id": u2["id"]})
    assert r.json()["user_id"] == u2["id"]
def test_delete_expense(client):
    u = make_user(client)
    c = make_category(client)
    e = make_expense(client, u["id"], c["id"])
    r = client.delete(f"/expenses/{e['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/expenses/{e['id']}")
    assert r2.status_code == 404
def test_payment_method_stored(client):
    u = make_user(client)
    c = make_category(client)
    e = make_expense(client, u["id"], c["id"], payment_method="Credit Card")
    assert e["payment_method"] == "Credit Card"
# ══════════════════════════════════════════════════════════════════════════════
#  MONTHLY SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def test_monthly_summary_total(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"], amount=20, date="2025-03-05")
    make_expense(client, u["id"], c["id"], amount=30, date="2025-03-20")
    make_expense(client, u["id"], c["id"], amount=99, date="2025-04-01")  # different month
    r = client.get("/expenses/summary/monthly", params={"year": 2025, "month": 3})
    assert r.status_code == 200
    assert r.json()["total"] == 50
def test_monthly_summary_filtered_by_user(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")
    c  = make_category(client)
    make_expense(client, u1["id"], c["id"], amount=100, date="2025-06-01")
    make_expense(client, u2["id"], c["id"], amount=200, date="2025-06-01")
    r = client.get("/expenses/summary/monthly",
                   params={"year": 2025, "month": 6, "user_id": u1["id"]})
    assert r.json()["total"] == 100
def test_monthly_summary_empty(client):
    r = client.get("/expenses/summary/monthly", params={"year": 2025, "month": 1})
    assert r.json()["total"] == 0
    assert r.json()["categories"] == []
# ══════════════════════════════════════════════════════════════════════════════
#  YEARLY REPORT
# ══════════════════════════════════════════════════════════════════════════════
def test_yearly_summary(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"], amount=100, date="2025-01-10")
    make_expense(client, u["id"], c["id"], amount=200, date="2025-07-15")
    make_expense(client, u["id"], c["id"], amount=999, date="2024-12-31")  # different year
    r = client.get("/reports/summary/year", params={"year": 2025})
    body = r.json()
    assert body["total"] == 300
    assert len(body["monthly"]) == 12
# ══════════════════════════════════════════════════════════════════════════════
#  TIMESERIES
# ══════════════════════════════════════════════════════════════════════════════
def test_timeseries(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"], amount=50,  date="2023-06-01")
    make_expense(client, u["id"], c["id"], amount=150, date="2024-06-01")
    make_expense(client, u["id"], c["id"], amount=250, date="2025-06-01")
    r = client.get("/reports/timeseries/years",
                   params={"from_year": 2023, "to_year": 2025})
    years = {y["year"]: y["total"] for y in r.json()["years"]}
    assert years[2023] == 50
    assert years[2024] == 150
    assert years[2025] == 250
def test_timeseries_invalid_range(client):
    r = client.get("/reports/timeseries/years",
                   params={"from_year": 2025, "to_year": 2023})
    assert r.status_code == 400
# ══════════════════════════════════════════════════════════════════════════════
#  BY-USER REPORT
# ══════════════════════════════════════════════════════════════════════════════
def test_by_user(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")
    c  = make_category(client)
    make_expense(client, u1["id"], c["id"], amount=300, date="2025-02-01")
    make_expense(client, u2["id"], c["id"], amount=700, date="2025-02-01")
    r = client.get("/reports/by-user", params={"year": 2025})
    users_map = {u["user_id"]: u["total"] for u in r.json()["users"]}
    assert users_map[u1["id"]] == 300
    assert users_map[u2["id"]] == 700
def test_by_user_all_listed_even_zero(client):
    u1 = make_user(client, "Alice", "alice@test.com")
    u2 = make_user(client, "Bob",   "bob@test.com")  # no expenses
    c  = make_category(client)
    make_expense(client, u1["id"], c["id"], amount=100, date="2025-01-01")
    r = client.get("/reports/by-user", params={"year": 2025})
    users_map = {u["user_id"]: u["total"] for u in r.json()["users"]}
    assert users_map.get(u2["id"]) == 0
def test_by_user_month_filter(client):
    u = make_user(client)
    c = make_category(client)
    make_expense(client, u["id"], c["id"], amount=100, date="2025-01-15")
    make_expense(client, u["id"], c["id"], amount=200, date="2025-02-15")
    r = client.get("/reports/by-user", params={"year": 2025, "month": 1})
    users_map = {uu["user_id"]: uu["total"] for uu in r.json()["users"]}
    assert users_map[u["id"]] == 100
 