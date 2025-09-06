from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.orm import mapped_column

# Аннотации для типов
uniq_str_an = Annotated[str, mapped_column(unique=True)]
content_an = Annotated[str | None, mapped_column(Text)]
big_int = Annotated[int, mapped_column(BigInteger)]
created_at_an = Annotated[datetime, mapped_column(DateTime, default=func.now())]
updated_at_an = Annotated[
    datetime,
    mapped_column(DateTime, default=func.now(), onupdate=func.now()),
]
