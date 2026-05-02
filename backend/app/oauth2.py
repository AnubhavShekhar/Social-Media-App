from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from dotenv import load_dotenv
from app.schemas import TokenData
from app.utils import get_user_by_id
import os
from app.database import DBConn
import logging

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM')

logger = logging.getLogger("app.oauth2")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    delta = expires_delta if expires_delta else timedelta(minutes=30)

    expire = datetime.now(timezone.utc) + delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    logger.info("access_token_created user_id=%s expires_in=%s", data.get("user_id"), int(delta.total_seconds()))

    return encoded_jwt, delta


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], conn: DBConn):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    
    try:
        if JWT_ALGORITHM is None:
            logger.exception("jwt_algorithm_missing")
            raise RuntimeError("JWT_ALGORITHM is not set")

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")

        if user_id is None:
            logger.warning("token_missing_user_id")
            raise credentials_exception
        
        token_data = TokenData(id = user_id)
    
    except ExpiredSignatureError:
        logger.warning("token_expired")
        raise credentials_exception
    except InvalidTokenError:
        logger.warning("token_invalid")
        raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        logger.exception("get_current_user_failed")
        raise credentials_exception
    
    user = await get_user_by_id(conn, token_data.id)

    if user is None:
        logger.warning("token_user_not_found user_id=%s", token_data.id)
        raise credentials_exception
    
    logger.info("token_validated user_id=%s", token_data.id)
    return user
