import app.categories.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.products.models  # noqa: F401
from app.auth.models import User
from app.cart.models import Cart
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password


def ensure_admin() -> User:
    settings = get_settings()
    email = settings.ADMIN_EMAIL
    password = settings.ADMIN_PASSWORD
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be set in the environment")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                name="Administrator",
                email=email,
                password_hash=hash_password(password),
                is_admin=True,
            )
            db.add(user)
            db.flush()
            cart = db.query(Cart).filter(Cart.user_id == user.id).first()
            if cart is None:
                db.add(Cart(user_id=user.id))
            print(f"Created admin user: {email}")
        else:
            user.is_admin = True
            print(f"Promoted existing user to admin: {email}")
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


if __name__ == "__main__":
    ensure_admin()
