import requests

from config import Config


class Translator:
    def __init__(self):
        self.content_type = 'application/json'

    def translate(self, word):
        iam_token = self._get_iam_yandex_token()

        headers = {
            'Content-Type': self.content_type,
            'Authorization': f'Bearer {iam_token}',
        }

        body = {
            'texts': [word],
            'targetLanguageCode': 'ru',
            'folderId': Config.YANDEX_FOLDER_ID,
        }

        return self._make_request_to_translate_api(
            headers,
            body
        )

    def _make_request_to_translate_api(self, headers, body):
        response = requests.post(
            Config.YANDEX_TRANSLATE_URL,
            json=body,
            headers=headers
        )

        return response.json()['translations'][0]['text']

    def _get_iam_yandex_token(self):
        body = {
            'yandexPassportOauthToken': Config.YANDEX_OAUTH_TOKEN,
        }

        response = requests.post(
            Config.YANDEX_GET_IAM_TOKEN_URL,
            json=body
        )

        return response.json()['iamToken']
