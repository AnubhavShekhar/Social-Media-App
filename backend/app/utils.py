from pwdlib import PasswordHash
from psycopg import AsyncConnection
from psycopg.rows import dict_row

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

async def get_user_by_id(conn: AsyncConnection, id : str):
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("""--sql
                          SELECT * FROM users WHERE id = %s"""
                          , (id, ))
        return await cur.fetchone()

def add_owner_info(response: dict, user):
    keys = ['email', 'created_at']
    response.update({"owner": {key : user[key] for key in keys if key in user}})
    
    return response