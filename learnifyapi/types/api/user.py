from typing import Any, Optional

from pydantic import Field

from learnifyapi.types.model import DT, Type


class User(Type):
    id: int
    user_id: int
    payed_at: Optional[DT] = None
    expires_at: Optional[DT] = None
    is_active: bool
    plan_type: str
