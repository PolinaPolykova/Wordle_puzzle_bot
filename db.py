# WARNING: USE THIS SCRIPT FOR CREATE DB ONLY!

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()


class Language(Base):
    __tablename__ = 'language'

    id = Column(Integer, primary_key=True)

    name_short = Column(String, nullable=False)
    name = Column(String, nullable=False)
    regex = Column(String, nullable=False)

    words = relationship('Word', back_populates='language')
    users = relationship('User', back_populates='language')


class Word(Base):
    __tablename__ = 'word'

    id = Column(Integer, primary_key=True)

    word = Column(String, nullable=False)

    language_id = Column(Integer, ForeignKey('language.id'), nullable=False)
    language = relationship('Language', back_populates='words')

    users = relationship('User', back_populates='current_word')


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    guessed_count = Column(Integer, nullable=False, default=0)
    retries = Column(Integer, nullable=False, default=0)

    language_id = Column(Integer, ForeignKey('language.id'), nullable=False)
    language = relationship('Language', back_populates='users')

    current_word_id = Column(Integer, ForeignKey('word.id'), nullable=True)
    current_word = relationship('Word', back_populates='users')


class UserUsedWord(Base):
    __tablename__ = 'user_used_word'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    word_id = Column(Integer, ForeignKey('word.id'))


def main():
    engine = create_engine('sqlite:///db.db', echo=True)

    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    languages = [
        {
            'name_short': 'ru',
            'name': 'русский',
            'regex': '[а-я]+',
        },
        {
            'name_short': 'en',
            'name': 'английский',
            'regex': '[a-z]+',
        }
    ]

    for item in languages:
        lang = Language(
            name_short=item['name_short'],
            name=item['name'],
            regex=item['regex']
        )

        session.add(lang)

        with open(f'words/words-{item["name_short"]}.txt', 'r') as f:
            for word in f:
                w = Word(
                    word=word.strip(),
                    language=lang
                )
                session.add(w)

    session.commit()


if __name__ == '__main__':
    main()
