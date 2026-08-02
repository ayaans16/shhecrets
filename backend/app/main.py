from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, sessions
from app.config import get_settings


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default handler echoes the invalid value back in the
    # response body (e.g. "input": "<whatever was sent>"). That's normal
    # for most APIs, but here the invalid input could be someone's secret
    # content (e.g. one byte over the length cap) - echoing it back would
    # violate "no plaintext secret content in ... error messages, ever."
    # So we strip the input value out of every validation error before it
    # goes back over the wire.
    errors = exc.errors(include_url=False)
    for error in errors:
        error.pop("input", None)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": errors})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="shhecrets")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)

    app.include_router(health.router)
    app.include_router(sessions.router)

    return app


# Module-level instance for `uvicorn app.main:app`. Tests import
# create_app() directly instead, so each test gets its own instance.
app = create_app()
