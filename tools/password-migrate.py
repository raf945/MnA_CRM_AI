from argon2 import PasswordHasher
import sqlalchemy
"""
def hashExistingPassword(user_id: int, password: str):
    ph = PasswordHasher()
    hashed_password = ph.hash(password)

    with database.begin() as conn:
        conn.execute(
            sqlalchemy.text(" UPDATE users SET password_hash = :password_hash WHERE id = :user_id"),
            {"password_hash": hashed_password, "user_id": user_id},
        )

hashExistingPassword(1, "12345")

"""