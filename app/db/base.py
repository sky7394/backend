from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so that Alembic and SQLAlchemy metadata can discover them
from app.models.user import User  # noqa: F401, E402
from app.models.exam import Exam  # noqa: F401, E402
from app.models.question import Question  # noqa: F401, E402
from app.models.learning_profile import LearningProfile  # noqa: F401, E402
from app.models.payment import Payment  # noqa: F401, E402
