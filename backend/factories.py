import uuid
from datetime import datetime, timezone

from factory.base import Factory 
from factory.declarations import LazyFunction
from faker import Faker

from app.models import Post, User

fake = Faker()

class UserFactory(Factory): 
    """
    Builds User model instances with realistic fake data.
    Does NOT touch the database — call the `create_*` async helpers in
    conftest.py to persist. We use plain factory.Factory (not
    SQLAlchemyModelFactory) because our session is async; we own persistence.
    """

    class Meta:
        model = User

    id = LazyFunction(uuid.uuid4)
    # fake.unique.email generates a different address on every call
    email = LazyFunction(lambda : fake.unique.email())
    password = LazyFunction(lambda : fake.password(length=12))
    created_at = LazyFunction(lambda : datetime.now(timezone.utc))

class PostFactory(Factory):
    """
    Builds Post model instances with realistic fake data
    `user_id` has no default - callers must always supply it so there's no 
    risk of accidentally creating a post with a null foreign key
    """

    class Meta:
        model = Post

    id = LazyFunction(uuid.uuid4)
    user_id = None # required - pass user_id = some_user.id at call site
    title = LazyFunction(lambda : fake.sentence(nb_words=4).rstrip("."))
    content = LazyFunction(lambda : fake.paragraph(nb_sentences=3))
    published = True
    created_at = LazyFunction(lambda : datetime.now(timezone.utc))
    image_url = None
    image_fileid = None