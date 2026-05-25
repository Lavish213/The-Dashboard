from fastapi import APIRouter, Depends

from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])
