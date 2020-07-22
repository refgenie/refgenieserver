import os
from sqlalchemy import create_engine, JSON
from contextlib import contextmanager

from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .main import _LOGGER

Base = declarative_base()


class Genome(Base):
    __tablename__ = 'genomes'
    id = Column(Integer)
    digest = Column(String(32), nullable=False, primary_key=True)
    alias = Column(String(50), nullable=False)
    description = Column(String(250), nullable=False)
    # one-to-many relationship between genome to assets
    assets = relationship('Asset', back_populates='genome')


class Asset(Base):
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(250), nullable=False)
    default_tag = relationship("Tag", uselist=False)
    tags = relationship('Tag')
    genome_digest = Column(String(32), ForeignKey('genomes.digest'))
    genome = relationship("Genome", back_populates="assets")


relationships = Table("relationships", Base.metadata,
    Column("relationship_id", Integer, primary_key=True),
    Column("child_id", Integer, ForeignKey("tags.id")),
    Column("parent_id", Integer, ForeignKey("tags.id"))
)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    archive_path = Column(String(50), nullable=False)
    seek_keys = Column(JSON, nullable=False)
    archive_digest = Column(String(32), nullable=False)
    asset_digest = Column(String(32), nullable=False)
    asset_size = Column(String(32), nullable=False)
    archive_size = Column(String(32), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'))
    # self-referential many-to-many relationship for parent-children
    parents = relationship("Tag",
                           secondary=relationships,
                           primaryjoin=id == relationships.c.child_id,
                           secondaryjoin=id == relationships.c.parent_id,
                           backref="children",
                           lazy="immediate")


DATABASE_URL = os.getenv('DATABASE_URL') \
               or 'postgresql://refgenomes-user:refgenomes-password@db/refgenomes'


engine = create_engine(DATABASE_URL, echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope_query():
    """
    Provide a transactional scope around a series of query
    operations, no commit afterwards.
    """
    session = Session()
    try:
        yield session
    except Exception as e:
        _LOGGER.error("Got exception, rolling back and rasing.")
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope_insert():
    """
    Provide a transactional scope around a series of operations with commit.
    """
    with session_scope_query() as session:
        yield session
        session.commit()
