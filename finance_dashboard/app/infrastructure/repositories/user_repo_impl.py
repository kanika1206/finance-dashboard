"""
User Repository — concrete implementation.
Paper applied: IEEE Clean Architecture ICoICT 2022
- Repository pattern isolates DB queries from business logic
- Each method has a single responsibility
- Returns None instead of raising on missing records — callers decide error behavior
"""
from sqlalchemy.orm import Session
from app.infrastructure.models.user_model import UserModel, RoleEnum, StatusEnum


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_by_email(self, email: str) -> UserModel | None:
        return self.db.query(UserModel).filter(UserModel.email == email).first()

    def get_all(self, page: int = 1, limit: int = 20) -> dict:
        query = self.db.query(UserModel)
        total = query.count()
        users = query.order_by(UserModel.created_at.desc())\
                     .offset((page - 1) * limit)\
                     .limit(limit)\
                     .all()
        return {"total": total, "page": page, "limit": limit, "data": users}

    def create(self, data: dict) -> UserModel:
        user = UserModel(**data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: str, data: dict) -> UserModel | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        for key, val in data.items():
            setattr(user, key, val)
        self.db.commit()
        self.db.refresh(user)
        return user

    def toggle_status(self, user_id: str) -> UserModel | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.status = (
            StatusEnum.inactive if user.status == StatusEnum.active else StatusEnum.active
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def email_exists(self, email: str) -> bool:
        return self.db.query(UserModel).filter(UserModel.email == email).count() > 0
