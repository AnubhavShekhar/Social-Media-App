from dotenv import load_dotenv
import psycopg 
import os

load_dotenv(dotenv_path='D:\\Programming\\Python\\Projects\\FASTAPI\\Social Media App\\app\\.env')

DB_SECRET = os.getenv('DB_SECRET')
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set")

# try:
#     with psycopg.connect(f"host=localhost user=postgres password={DB_SECRET} dbname=postgres", autocommit=True) as conn:
#         with conn.cursor() as cur:
#             cur.execute("CREATE DATABASE social_media_app")
#             print("Database created successfully")
# except Exception as e:
#     print(f"ERROR: {e}")

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""--sql
                        CREATE TABLE IF NOT EXISTS posts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        published BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                        );""")
            print("posts table created succesfully")
except Exception as e:
    print(f"ERROR: {e}")

# try:
#     with psycopg.connect(DATABASE_URL) as conn:
#         with conn.cursor() as cur:
#             cur.execute("""--sql
#                         INSERT INTO posts (title, content) 
#                         VALUES 
#                         ('project hail mary', 'amaze amaze amaze'),
#                         ('dark knight', 'let''s put a smile on that face'),
#                         ('Fast and Furious', 'Family');
#                         """)
#         print("values inserted succesfully")
# except Exception as e:
#     print(f"ERROR: {e}")

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""--sql
                        CREATE TABLE IF NOT EXISTS users(
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """)
            print("users table created successfully")
except Exception as e:
    print(f"ERROR: {e}")