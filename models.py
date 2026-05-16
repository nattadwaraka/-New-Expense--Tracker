from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
import database

class User(database.Base):
    __tablename__ = "users"
    id    = Column(Integer, primary_key=True, index=True)
    name  = Column(String(120), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=False, default="")
    # One user → many expenses; delete user → delete its expenses
    expenses = relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Category(database.Base):
    __tablename__ = "categories"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(300), nullable=False, default="")
    # Delete is blocked by the route if any expense references this category
    expenses = relationship("Expense", back_populates="category")

class Expense(database.Base):
    __tablename__ = "expenses"
    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String(200), nullable=False)
    amount         = Column(Float,  nullable=False)
    date           = Column(Date,   nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id",      ondelete="CASCADE"), nullable=False)
    category_id    = Column(Integer, ForeignKey("categories.id"), nullable=False)
    notes          = Column(Text,   nullable=False, default="")
    payment_method = Column(String(60), nullable=False, default="")
    user     = relationship("User",     back_populates="expenses")
    category = relationship("Category", back_populates="expenses")