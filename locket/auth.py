# locket/auth.py
import json
import uuid
import requests

class Auth:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.device_id = self.generate_device_id()
        self.token = None

    @staticmethod
    def generate_device_id():
        return str(uuid.uuid4()).upper()

    def create_token(self):
        request_data = {
            "email": self.email,
            "password": self.password,
            "clientType": "CLIENT_TYPE_IOS",
            "returnSecureToken": True
        }

        url = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyCQngaaXQIfJaH0aS2l7REgIjD7nL431So"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en",
            "baggage": "sentry-environment=production,sentry-public_key=78fa64317f434fd89d9cc728dd168f50,sentry-release=com.locket.Locket@1.82.0+3,sentry-trace_id=90310ccc8ddd4d059b83321054b6245b",
            "Connection": "keep-alive",
            "Content-Length": "117",
            "Content-Type": "application/json",
            "Host": "www.googleapis.com",
            "sentry-trace": "90310ccc8ddd4d059b83321054b6245b-3a4920b34e94401d-0",
            "User-Agent": "FirebaseAuth.iOS/10.23.1 com.locket.Locket/1.82.0 iPhone/18.0 hw/iPhone12_1",
            "X-Client-Version": "iOS/FirebaseSDK/10.23.1/FirebaseCore-iOS",
            'X-Firebase-AppCheck': 'eyJlcnJvciI6IlVOS05PV05fRVJST1IifQ==',
            "X-Firebase-GMPID": "1:641029076083:ios:cc8eb46290d69b234fa606",
            "X-Ios-Bundle-Identifier": "com.locket.Locket"
        }

        response = requests.post(url, headers=headers, json=request_data, timeout=(10, 20))

        if response.ok:
            self.token = response.json().get('idToken')
            # print(f"Firebase Token: {self.token}")
            return self.token
        else:
            raise Exception('Failed to login')

    def get_token(self):
        # if not self.token:
        #     self.create_token()
        # return self.token
        return self.create_token()