from __future__ import annotations
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import extract, func
from sqlalchemy.orm import Session
import models
import schemas
import database 
from database import Base, engine
from database import get_db
from datetime import date
# ── Bootstrap database ────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
  # safe no-op when schema is current
# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Expense Dashboard API",
    description="Full-stack expense tracker – FastAPI + SQLAlchemy + SQLite",
    version="1.0.0",
)

# ══════════════════════════════════════════════════════════════════════════════
#  FRONTEND  (serve index.html at /)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse("index.html")

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ══════════════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/users", response_model=schemas.UserOut, status_code=201, tags=["Users"])
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = models.User(**body.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/users", response_model=List[schemas.UserOut], tags=["Users"])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.name).all()

@app.get("/users/{user_id}", response_model=schemas.UserOut, tags=["Users"])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user

@app.put("/users/{user_id}", response_model=schemas.UserOut, tags=["Users"])
def update_user(user_id: int, body: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    data = body.model_dump(exclude_none=True)
    if "email" in data:
        conflict = db.query(models.User).filter_by(email=data["email"]).first()
        if conflict and conflict.id != user_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already in use")
    for key, val in data.items():
        setattr(user, key, val)
    db.commit()
    db.refresh(user)
    return user

@app.delete("/users/{user_id}", status_code=204, tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db.delete(user)   # cascade deletes expenses via ORM relationship
    db.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/categories", response_model=schemas.CategoryOut, status_code=201, tags=["Categories"])
def create_category(body: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if db.query(models.Category).filter_by(name=body.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category name already exists")
    cat = models.Category(**body.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@app.get("/categories", response_model=List[schemas.CategoryOut], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.name).all()

@app.get("/categories/{category_id}", response_model=schemas.CategoryOut, tags=["Categories"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return cat

@app.put("/categories/{category_id}", response_model=schemas.CategoryOut, tags=["Categories"])
def update_category(category_id: int, body: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    data = body.model_dump(exclude_none=True)
    if "name" in data:
        conflict = db.query(models.Category).filter_by(name=data["name"]).first()
        if conflict and conflict.id != category_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category name already in use")
    for key, val in data.items():
        setattr(cat, key, val)
    db.commit()
    db.refresh(cat)
    return cat

@app.delete("/categories/{category_id}", status_code=204, tags=["Categories"])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    if db.query(models.Expense).filter_by(category_id=category_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete a category that is used by expenses")
    db.delete(cat)
    db.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  EXPENSES  (summary route MUST come before /{expense_id})
# ══════════════════════════════════════════════════════════════════════════════
@app.get(
    "/expenses/summary/monthly",
    response_model=schemas.MonthlySummaryOut,
    tags=["Reports"],
    summary="Category totals for one calendar month",
)
def monthly_summary(
    year:    int           = Query(..., ge=2000, le=2100),
    month:   int           = Query(..., ge=1,    le=12),
    user_id: Optional[int] = Query(None),
    db:      Session       = Depends(get_db),
):
    q = (
        db.query(
            models.Expense.category_id,
            func.sum(models.Expense.amount).label("total"),
        )
        .filter(
            extract("year",  models.Expense.date) == year,
            extract("month", models.Expense.date) == month,
        )
    )
    if user_id:
        q = q.filter(models.Expense.user_id == user_id)
    rows = q.group_by(models.Expense.category_id).all()
    grand_total = sum(r.total for r in rows)
    return {
        "year":       year,
        "month":      month,
        "total":      grand_total,
        "categories": [{"category_id": r.category_id, "total": r.total} for r in rows],
    }

@app.post("/expenses", response_model=schemas.ExpenseOut, status_code=201, tags=["Expenses"])
def create_expense(body: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    
 # ✅ Block future dates
    if body.date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Future dates are not allowed"
        )

    if not db.get(models.User, body.user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not db.get(models.Category, body.category_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    expense = models.Expense(**body.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

@app.get("/expenses", response_model=List[schemas.ExpenseOut], tags=["Expenses"])
def list_expenses(
    user_id: Optional[int] = Query(None),
    db:      Session       = Depends(get_db),
):
    q = db.query(models.Expense)
    if user_id:
        q = q.filter_by(user_id=user_id)
    return q.order_by(models.Expense.date.desc(), models.Expense.id.desc()).all()

@app.get("/expenses/{expense_id}", response_model=schemas.ExpenseOut, tags=["Expenses"])
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return expense

@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseOut, tags=["Expenses"])
def update_expense(expense_id: int, body: schemas.ExpenseUpdate, db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    data = body.model_dump(exclude_none=True)
    
    if "date" in data and data["date"] > date.today():
        raise HTTPException(
            status_code=400,
            detail="Future dates are not allowed"
        )

    if "user_id" in data and not db.get(models.User, data["user_id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if "category_id" in data and not db.get(models.Category, data["category_id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    for key, val in data.items():
        setattr(expense, key, val)
    db.commit()
    db.refresh(expense)
    return expense

@app.delete("/expenses/{expense_id}", status_code=204, tags=["Expenses"])
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    db.delete(expense)
    db.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════════════════════════
@app.get(
    "/reports/summary/year",
    response_model=schemas.YearlySummaryOut,
    tags=["Reports"],
    summary="Full-year totals + category breakdown + 12 monthly points",
)
def yearly_summary(
    year:    int           = Query(..., ge=2000, le=2100),
    user_id: Optional[int] = Query(None),
    db:      Session       = Depends(get_db),
):
    base = db.query(models.Expense).filter(
        extract("year", models.Expense.date) == year
    )
    if user_id:
        base = base.filter(models.Expense.user_id == user_id)
    grand_total = base.with_entities(func.sum(models.Expense.amount)).scalar() or 0.0
    cat_rows = (
        base.with_entities(
            models.Expense.category_id,
            func.sum(models.Expense.amount).label("total"),
        )
        .group_by(models.Expense.category_id)
        .all()
    )
    month_rows = (
        base.with_entities(
            extract("month", models.Expense.date).label("m"),
            func.sum(models.Expense.amount).label("total"),
        )
        .group_by("m")
        .all()
    )
    month_map = {int(r.m): r.total for r in month_rows}
    return {
        "year":       year,
        "total":      grand_total,
        "categories": [{"category_id": r.category_id, "total": r.total} for r in cat_rows],
        "monthly":    [{"month": m, "total": month_map.get(m, 0.0)} for m in range(1, 13)],
    }

@app.get(
    "/reports/timeseries/years",
    response_model=schemas.TimeseriesOut,
    tags=["Reports"],
    summary="One total per calendar year in an inclusive range",
)
def timeseries_years(
    from_year: int           = Query(..., ge=2000, le=2100),
    to_year:   int           = Query(..., ge=2000, le=2100),
    user_id:   Optional[int] = Query(None),
    db:        Session       = Depends(get_db),
):
    if from_year > to_year:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "from_year must be ≤ to_year")
    q = (
        db.query(
            extract("year", models.Expense.date).label("yr"),
            func.sum(models.Expense.amount).label("total"),
        )
        .filter(
            extract("year", models.Expense.date) >= from_year,
            extract("year", models.Expense.date) <= to_year,
        )
    )
    if user_id:
        q = q.filter(models.Expense.user_id == user_id)
    rows = q.group_by("yr").order_by("yr").all()
    year_map = {int(r.yr): r.total for r in rows}
    return {
        "from_year": from_year,
        "to_year":   to_year,
        "years":     [{"year": y, "total": year_map.get(y, 0.0)} for y in range(from_year, to_year + 1)],
    }

@app.get(
    "/reports/by-user",
    response_model=schemas.ByUserOut,
    tags=["Reports"],
    summary="Spend per profile — full year or a single month",
)
def by_user(
    year:  int           = Query(..., ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    db:    Session       = Depends(get_db),
):
    q = (
        db.query(
            models.Expense.user_id,
            func.sum(models.Expense.amount).label("total"),
        )
        .filter(extract("year", models.Expense.date) == year)
    )
    if month:
        q = q.filter(extract("month", models.Expense.date) == month)
    rows = q.group_by(models.Expense.user_id).all()
    spend_map = {r.user_id: r.total for r in rows}
    all_users = db.query(models.User).order_by(models.User.name).all()
    return {
        "year":  year,
        "month": month,
        "users": [
            {"user_id": u.id, "name": u.name, "total": spend_map.get(u.id, 0.0)}
            for u in all_users
        ],
    }