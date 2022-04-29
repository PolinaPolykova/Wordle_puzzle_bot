def get_participant_correct_case(count):
    if (count % 10) == 1 and (count % 100) != 11:
        return 'участника'
    else:
        return 'участников'


def get_retries_correct_case(count):
    if (count % 10) == 1:
        return 'попытки'
    else:
        return 'попыток'


def get_word_correct_case(count):
    if (count % 100) in set([11, 12, 13, 14]):
        return 'слов'

    count10 = count % 10
    if count10 == 1:
        return 'слово'
    elif count10 in (2, 3, 4):
        return 'слова'
    elif count10 == 0 or (count10 > 4 and count10 < 10):
        return 'слов'
