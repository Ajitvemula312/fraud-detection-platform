from __future__ import annotations

from fraud_platform.config import AppConfig


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "uvicorn is not installed. Install optional API dependencies with "
            "`pip install -e \".[api]\"`."
        ) from exc
    from fraud_platform.api.app import create_app

    config = AppConfig()
    uvicorn.run(create_app(), host="0.0.0.0", port=config.api_port)


if __name__ == "__main__":
    main()

