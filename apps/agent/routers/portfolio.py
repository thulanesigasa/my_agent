"""Private, locally saved portfolio configuration."""

from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_api_key
from core.store import ConflictError
from services.proposals import Portfolio, portfolio, save_portfolio

router = APIRouter(
    prefix="/api/portfolio", tags=["Portfolio"], dependencies=[Depends(verify_api_key)]
)


@router.get("")
def get_catalog():
    return portfolio()


@router.put("")
def update_catalog(payload: Portfolio):
    try:
        return save_portfolio(payload)
    except ConflictError as exc:
        raise HTTPException(409, str(exc))
