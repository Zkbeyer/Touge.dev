from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False


class UserResponse(BaseModel):
    id: str
    github_username: str
    display_name: str | None
    email: str | None
    timezone: str
    streak: int
    longest_streak: int
    total_points: int
    spendable_points: int
    gas: int
    leetcode_validated: bool
    leetcode_username: str | None
    active_car_id: str | None
