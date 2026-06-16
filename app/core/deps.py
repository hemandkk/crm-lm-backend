

def get_current_user(password: str):
    return pwd_context.hash(password)


def require_admin(
    current_user=Depends(
        get_current_user
    )
):
    if current_user.role != "admin":
        raise HTTPException(
            403,
            "Forbidden"
        )

    return current_user