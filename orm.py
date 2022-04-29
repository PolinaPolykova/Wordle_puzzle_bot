import random
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config
from db import Language, User, UserUsedWord, Word


class ORM:
    def __init__(self):
        self._session = self._create_session()

    def _create_session(self):
        engine = create_engine('sqlite:///db.db', echo=True)
        return scoped_session(sessionmaker(bind=engine))

    def get_all_languages(self):
        return self._session.query(Language).all()

    def get_language_by_name(self, name):
        return self._session.query(Language)\
            .filter(Language.name==name).first()

    def get_language_default(self):
        return self._session.query(Language)\
            .filter(Language.name_short==Config.LANGUAGE_DEFAULT)\
            .first()

    def get_user_by_tid(self, tid):
        return self._session.query(User).get(tid)

    def create_user(self, tid, name):
        language = self.get_language_default()

        user = User(
            id=tid,
            name=name,
            language=self.get_language_default(),
            current_word=self.get_random_word(language)
        )

        self._session.add(user)
        self._session.commit()

    def update_user(self, user):
        self._session.add(user)
        self._session.commit()

    def get_user_rating(self, user):
        users = self._session.query(User)\
            .order_by(User.guessed_count.desc())
        for i, item in enumerate(users):
            if item.id == user.id:
                return i + 1, users.count()

    def get_random_word(self, language):
        words = self._session.query(Word)\
            .filter(Word.language_id==language.id)
        words_ids = [w.id for w in words]
        rid = random.randint(0, len(words_ids))
        wid = words_ids[rid]
        return self._session.query(Word).get(wid)

    def is_word_exists(self, word):
        w = self._session.query(Word)\
            .filter(Word.word==word)\
            .first()
        return w is not None

    def get_next_user_word(self, user):
        user_words = set([
            item.word_id for item in self._session.query(UserUsedWord)
                .filter(UserUsedWord.user_id==user.id)
        ])

        words = self._session.query(Word)\
            .filter(Word.language_id==user.language_id)
        words_ids = [w.id for w in words]

        retries = 0
        while retries < len(words_ids):
            retries += 1
            rid = random.randint(0, len(words_ids))
            wid = words_ids[rid]
            if wid in user_words:
                continue

            return self._session.query(Word).get(wid)

        return None

    def set_user_used_word(self, user, word):
        uuw = UserUsedWord(
            user_id=user.id,
            word_id=word.id
        )
        self._session.add(uuw)
        self._session.commit()

    def add_words(self, source_path, language):
        all_words = set([
            item.word for item in self._session.query(Word)
                .filter(Word.language_id == language.id)
        ])

        count = 0

        with open(source_path, 'r') as f:
            for word in f:
                word_cleaned = word.strip().lower()

                if not word_cleaned:
                    continue

                if len(word_cleaned) != Config.WORD_LENGTH:
                    continue

                m = re.match(language.regex, word_cleaned)
                if not m:
                    continue

                if m.group(0) != word_cleaned:
                    continue

                if word_cleaned in all_words:
                    continue

                count += 1

                w = Word(
                    word=word_cleaned,
                    language=language
                )
                self._session.add(w)

        self._session.commit()

        return count
