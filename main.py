import os
from collections import Counter

from telegram import File, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler, Updater

from config import Config
from orm import ORM
from translate import Translator
from utils import (
    get_participant_correct_case, get_retries_correct_case, get_word_correct_case
)


CHANGE_LANGUAGE_FIRST = 0
CHANGE_LANGUAGE_SECOND = 1
UPLOAD_WORDS_FIRST = 0
UPLOAD_WORDS_SECOND = 1


def guess(update, context):
    print(update.message)

    user = db_orm.get_user_by_tid(
        update.message.chat.id
    )

    if user is None:
        update.message.reply_text(
            'Ошибка: кажется, вас не существует.'
        )
        return

    if user.current_word is None:
        update.message.reply_text(
            'Для вас ничего не загадано, '
            'потому что вы отгадали все слова на '
            'вашем текущем языке. Попробуйте сменить язык!'
        )
        return

    msg = update.message.text.strip().lower()
    if len(msg) != Config.WORD_LENGTH:
        update.message.reply_text(
            'Ошибка: длина слова должна быть 5 символов!'
        )
        return

    if not db_orm.is_word_exists(msg):
        update.message.reply_text(
            'Ошибка: такого слова не существует!'
        )
        return

    user.retries += 1

    word = user.current_word.word
    word_counter = Counter(word)
    result = list()

    for c1, c2 in zip(msg, word):
        if c1 == c2:
            result.append(c1)
        elif c1 in word_counter:
            result.append('*')
        else:
            result.append('-')

    result_counter = Counter(result)

    for i in range(len(result)):
        if result[i] != '*':
            continue

        c = msg[i]
        if word_counter[c] <= result_counter[c]:
            result[i] = '-'

    reply = ''.join(result)
    update.message.reply_text(reply)

    if reply == word:
        update.message.reply_text(
            f'Поздравляю! Вы угадали слово с {user.retries} попытки.'
        )
        user.guessed_count += 1
    elif user.retries >= Config.MAX_RETRIES:
        update.message.reply_text(
            'Попытки закончились, вы не угадали! Теперь загадано новое слово.'
        )

    if reply == word or user.retries >= Config.MAX_RETRIES:
        user.retries = 0
        db_orm.set_user_used_word(
            user,
            user.current_word
        )
        user.current_word = db_orm.get_next_user_word(user)

    db_orm.update_user(user)


def get_all_languages_names():
    return [item.name for item in db_orm.get_all_languages()]


def get_default_keyboard():
    return ReplyKeyboardMarkup(
        [
            ['/help', '/stat', '/translate'],
            ['/changelanguage', '/uploadwords'],
        ],
        resize_keyboard=True
    )


def cancel_scenario(update, context, text):
    update.message.reply_text(
        f'Вы отменили {text}.',
        reply_markup=get_default_keyboard()
    )

    return ConversationHandler.END


def change_language_start(update, context):
    update.message.reply_text(
        'Менять язык лучше всего СРАЗУ после того, '
        'как вы угадали или не угадали слово. '
        'Будет загадано новое слово.\n\n'
        'При смене языка слово, '
        'которое вы угадываете на текущем языке, '
        'будет считаться неугаданным, '
        'ЕСЛИ вы уже использовали попытки.\n\n'
        'Вы уверены, что хотите продолжить?',
        reply_markup=ReplyKeyboardMarkup(
            [['да', 'нет']],
            resize_keyboard=True
        )
    )

    return CHANGE_LANGUAGE_FIRST


def change_language_first(update, context):
    answer_continue = update.message.text
    if answer_continue == 'нет':
        return change_language_end(update, context)

    all_languages_names = get_all_languages_names()
    update.message.reply_text(
        'Выберите язык, на котором будут загадываться слова. '
        'Для отмены нажмите /cancel',
        reply_markup=ReplyKeyboardMarkup(
            [all_languages_names],
            resize_keyboard=True
        )
    )

    return CHANGE_LANGUAGE_SECOND


def change_language_second(update, context):
    user = db_orm.get_user_by_tid(update.message.chat.id)

    language_name = update.message.text
    if user.language.name == language_name:
        update.message.reply_text(
            'Вы выбрали тот же язык, что и был, '
            'поэтому ничего не поменялось!',
            reply_markup=get_default_keyboard()
        )
        return ConversationHandler.END

    language = db_orm.get_language_by_name(language_name)
    user.language = language
    db_orm.update_user(user)

    if user.retries > 0:
        db_orm.set_user_used_word(
            user,
            user.current_word
        )

    user.retries = 0
    user.current_word = db_orm.get_next_user_word(user)

    update.message.reply_text(
        'Язык успешно изменён!',
        reply_markup=get_default_keyboard()
    )

    return ConversationHandler.END


def change_language_end(update, context):
    return cancel_scenario(
        update,
        context,
        'изменение языка'
    )


def upload_words_start(update, context):
    all_languages_names = get_all_languages_names()

    update.message.reply_text(
        'Выберите язык, на котором вы хотите '
        'добавить новые слова в словарь. '
        'Для отмены нажмите /cancel',
        reply_markup=ReplyKeyboardMarkup(
            [all_languages_names],
            resize_keyboard=True
        )
    )

    return UPLOAD_WORDS_FIRST

def upload_words_first(update, context):
    language_name = update.message.text
    context.user_data['language'] = language_name

    update.message.reply_text(
        f'Пришлите, пожалуйста, файл со словами на языке `{language_name}`. '
        'Файл должен быть в формате .txt и каждое слово '
        'должно быть на отдельной строке. '
        'Для отмены нажмите /cancel',
        reply_markup=get_default_keyboard()
    )

    return UPLOAD_WORDS_SECOND


def upload_words_second(update, context):
    document = update.message.document
    file = document.get_file()
    file_path = f'files/{document.file_name}'
    filename = file.download(
        custom_path=file_path
    )

    language_name = context.user_data['language']
    language = db_orm.get_language_by_name(language_name)
    count = db_orm.add_words(
        filename,
        language
    )

    os.remove(file_path)

    update.message.reply_text(
        f'Вы успешно добавили {count} {get_word_correct_case(count)} '
        f'на языке `{language_name}`!'
    )

    context.user_data.clear()

    return ConversationHandler.END


def upload_words_end(update, context):
    context.user_data.clear()

    return cancel_scenario(
        update,
        context,
        'добавление файла'
    )


def translate_word(update, context):
    user = db_orm.get_user_by_tid(update.message.chat.id)

    if user.language.name_short == Config.LANGUAGE_DEFAULT:
        update.message.reply_text(
            'Хорошая попытка считерить! '
            'Перевести слово с русского на русский не получится :)'
        )
        return

    result = translator.translate(user.current_word.word)

    update.message.reply_text(result)


def stat(update, context):
    user = db_orm.get_user_by_tid(update.message.chat.id)
    rating, all_count = db_orm.get_user_rating(user)
    update.message.reply_text(
        f'Вы угадали {user.guessed_count} {get_word_correct_case(user.guessed_count)} '
        f'и занимаете {rating} место из {all_count} {get_participant_correct_case(all_count)}!'
    )


def help(update, context):
    user = db_orm.get_user_by_tid(update.message.chat.id)

    update.message.reply_text(
        f'{Config.RULES}\n\n'
        f'Текущее количество попыток: {user.retries}\n'
        f'Текущий язык: {user.language.name}'
    )


def start(update, context):
    user_name = update.message.chat.username if update.message.chat.username else update.message.chat.first_name

    update.message.reply_text(
        f'Привет, {user_name}! Это бот по популярной игре Wordle.\n\n'
        f'{Config.RULES}\n\n'
        'Игра уже началась!',
        reply_markup = get_default_keyboard()
    )

    tid = update.message.chat.id

    if db_orm.get_user_by_tid(tid) is None:
        db_orm.create_user(
            update.message.chat.id,
            user_name
        )


def main():
    all_languages_names = get_all_languages_names()
    languages_regex = '|'.join(all_languages_names)

    updater = Updater(Config.TELEGRAM_BOT_TOKEN)

    dp = updater.dispatcher

    conversation_upload_words = ConversationHandler(
        entry_points=[CommandHandler(
            'uploadwords',
            upload_words_start
        )],
        states={
            UPLOAD_WORDS_FIRST: [MessageHandler(
                Filters.regex(f'^({languages_regex})$'),
                upload_words_first,
                pass_user_data=True
            )],
            UPLOAD_WORDS_SECOND: [MessageHandler(
                Filters.document.txt,
                upload_words_second,
                pass_user_data=True
            )],
        },
        fallbacks=[CommandHandler(
            'cancel',
            upload_words_end
        )]
    )

    conversation_change_language = ConversationHandler(
        entry_points=[CommandHandler(
            'changelanguage',
            change_language_start
        )],
        states={
            CHANGE_LANGUAGE_FIRST: [MessageHandler(
                Filters.regex(f'^(да|нет)$'),
                change_language_first
            )],
            CHANGE_LANGUAGE_SECOND: [MessageHandler(
                Filters.regex(f'^({languages_regex})$'),
                change_language_second
            )],
        },
        fallbacks=[CommandHandler(
            'cancel',
            change_language_end
        )]
    )

    dp.add_handler(conversation_change_language)
    dp.add_handler(conversation_upload_words)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('stat', stat))
    dp.add_handler(CommandHandler('translate', translate_word))

    dp.add_handler(MessageHandler(Filters.text, guess))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    translator = Translator()
    db_orm = ORM()
    main()
