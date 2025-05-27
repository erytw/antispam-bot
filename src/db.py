from sqlalchemy import Column, Integer, Boolean, UniqueConstraint, select, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

Base = declarative_base()


class User(Base):  # type: ignore
    """
    User model representing a Telegram user.

    Attributes:
        id: Primary key of the user
        user_id: Telegram user ID
        searches: Relationship to user's search history
    """

    # pylint: disable=too-few-public-methods
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    has_nonspam_mesages = Column(Boolean)
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="_chat_user_combination"),
    )


def init_db(database_url="sqlite+aiosqlite:///chat_allowance.db"):
    """Initialize the database and return an async session factory."""
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    return async_session, init_tables


async def get_message_status(session: AsyncSession, chat_id: int, user_id: int) -> bool:
    """
    Check if the user has any non-spam messages.

    Args:
        session: SQLAlchemy async session
        chat_id: Telegram chat ID
        user_id: Telegram user ID

    Returns:
        True if the user has non-spam messages, False otherwise
    """
    result = await session.execute(
        select(User.has_nonspam_mesages).where(
            User.chat_id == chat_id, User.user_id == user_id
        )
    )
    scalar_result = result.scalar_one_or_none()
    return 0 if scalar_result is None else scalar_result


async def set_message_status(
    session: AsyncSession, chat_id: int, user_id: int, has_nonspam_mesages: bool
) -> None:
    """
    Set the message status for a user.

    Args:
        session: SQLAlchemy async session
        chat_id: Telegram chat ID
        user_id: Telegram user ID
        has_nonspam_mesages: True if the user has non-spam messages, False otherwise
    """
    user = await session.scalar(
        select(User).where(User.chat_id == chat_id, User.user_id == user_id)
    )
    if user:
        user.has_nonspam_mesages = has_nonspam_mesages
    else:
        user = User(
            chat_id=chat_id, user_id=user_id, has_nonspam_mesages=has_nonspam_mesages
        )
        session.add(user)
    await session.commit()
