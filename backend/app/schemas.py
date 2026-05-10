from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Literal
import uuid
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr 
    password : str = Field(min_length=1)

class UserResponse(BaseModel):
    id: uuid.UUID
    email : EmailStr
    created_at : datetime

    model_config = ConfigDict(from_attributes=True)

class UserOut(BaseModel):
    id : uuid.UUID
    email : EmailStr
    created_at : datetime 

class Post(BaseModel):
    id : uuid.UUID = Field(default_factory=uuid.uuid4)
    title : str
    content : str
    published : bool = True

class PostBase(BaseModel):
    id : uuid.UUID
    title : str
    content : str
    created_at : datetime
    published: bool
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

class PostsResponse(Post):
    created_at : datetime
    owner_id : uuid.UUID
    owner_email : EmailStr
    owner_created_at: datetime

class PostResponse(Post):
    created_at : datetime
    image_url : str | None = None
    user_id : uuid.UUID
    owner: dict


class PostWithVotes(BaseModel):
    post : PostBase
    owner: UserResponse
    votes: int

    model_config = ConfigDict(from_attributes=True)    

class UserLogin(UserCreate):
    pass

class Token(BaseModel):
    access_token : str
    token_type : str
    expires_in : int

class TokenData(BaseModel):
    id : str

class Vote(BaseModel):
    post_id : uuid.UUID
    dir : Literal[0, 1]      

class UserWithPostsResponse(UserResponse):
    posts: list[PostBase]

    model_config = ConfigDict(from_attributes=True)