from fastapi import HTTPException, status, APIRouter, Depends
from app.schemas import UserLogin, Token
from psycopg.rows import dict_row
from typing import Annotated
from ..utils import verify_password, hash_password
from app.oauth2 import create_access_token
from fastapi.security import OAuth2PasswordRequestForm
from app.database import DBConn
import logging

logger = logging.getLogger("app.auth")
router = APIRouter(prefix='/login', tags=['Login'])

DUMMY_HASH = hash_password('dummypassword')

@router.post('/', status_code=status.HTTP_200_OK)
async def login(user_credentials: Annotated[OAuth2PasswordRequestForm, Depends()], conn: DBConn):
    logger.info("login_requested email=%s", user_credentials.username)
    try:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("""--sql
                              SELECT * FROM users WHERE email = %s
                              """, (user_credentials.username,)
                            )
            
            user = await cur.fetchone()

            if user is None:
                # used to negate timing attacks
                verify_password(user_credentials.password, DUMMY_HASH)
                logger.warning("login_invalid_credentials email=%s", user_credentials.username)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Credentials"
                )
            
            if not verify_password(user_credentials.password, user['password']):
                logger.warning("login_invalid_credentials email=%s user_id=%s", user_credentials.username, user['id'])
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid Credentials'
                )
            
        access_token, delta = create_access_token(data={"user_id" : str(user['id'])})
        logger.info(
            "login_succeeded user_id=%s email=%s expires_in=%s",
            user['id'],
            user_credentials.username, int(delta.total_seconds())
        )
            
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(delta.total_seconds())
        )
    
    except HTTPException:
        raise
    except Exception:
        logger.exception("login_failed email=%s", user_credentials.username)
        raise