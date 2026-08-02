import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongo_client import get_db
from app.core.rate_limit import rate_limit_create, rate_limit_read
from app.core.redis_client import get_redis
from app.models.session import SecretReadResponse, SecretSubmission, SessionCreateResponse
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionCreateResponse,
    dependencies=[Depends(rate_limit_create)],
)
async def create_session(
    request: Request,
    redis_client: redis.Redis = Depends(get_redis),
    mongo_db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionCreateResponse:
    client_ip = request.client.host if request.client else None
    session_id, expires_at = await session_service.create_session(redis_client, mongo_db, client_ip)
    return SessionCreateResponse(session_id=session_id, expires_at=expires_at)


@router.put("/{session_id}/secret", status_code=status.HTTP_204_NO_CONTENT)
async def submit_secret(
    session_id: str,
    submission: SecretSubmission,
    redis_client: redis.Redis = Depends(get_redis),
) -> None:
    # Not rate-limited: the spec calls out create and read as the
    # enumeration-risk endpoints (rate_limit.py explains why). Submitting
    # requires already knowing a valid, unguessable session ID, so it
    # isn't a path to discovering *other* people's sessions - worth
    # revisiting if this needs limiting for other reasons later (e.g.
    # storage-spam by a party who does hold a valid link).
    await session_service.set_secret(redis_client, session_id, submission.content)


@router.get(
    "/{session_id}",
    response_model=SecretReadResponse,
    dependencies=[Depends(rate_limit_read)],
)
async def read_secret(
    session_id: str,
    redis_client: redis.Redis = Depends(get_redis),
    mongo_db: AsyncIOMotorDatabase = Depends(get_db),
) -> SecretReadResponse:
    content = await session_service.read_and_burn(redis_client, mongo_db, session_id)
    return SecretReadResponse(content=content)
