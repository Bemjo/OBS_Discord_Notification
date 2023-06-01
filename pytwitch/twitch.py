import requests
from typing import Optional, Tuple, List, Union
from enum import Enum


class Twitch:
    class Limits(int, Enum):
        UserRequests = 100
        VideoRequests = 100
        GamesRequests = 100


    class APIURL(str, Enum):
        AuthToken = r'https://id.twitch.tv/oauth2/token'
        RevokeToken = r'https://id.twitch.tv/oauth2/revoke'
        ValidateToken = r'https://id.twitch.tv/oauth2/validate'
        Users = r'https://api.twitch.tv/helix/users'
        Channels = r'https://api.twitch.tv/helix/channels'
        Videos = r'https://api.twitch.tv/helix/videos'
        Games = r'https://api.twitch.tv/helix/games'


    class Scope(str, Enum):
        AnalyticsExtentions = 'analytics:read:extensions'
        AnalyticsGames = 'analytics:read:games'
        Bits = 'bits:read'
        ChannelCommercial = 'channel:edit:commercial'
        ChannelBroadcast = 'channel:manage:broadcast'
        ChannelExtentions = 'channel:manage:extensions'
        ChannelManageRedemptions = 'channel:manage:redemptions'
        ChannelVideos = 'channel:manage:videos'
        ChannelEditors = 'channel:read:editors'
        ChannelHypeTrain = 'channel:read:hype_train'
        ChannelReadRedemptions = 'channel:read:redemptions'
        ChannelStreamKey = 'channel:read:stream_key'
        ChannelSubscriptions = 'channel:read:subscriptions'
        Clips = 'clips:edit'
        Moderation = 'moderation:read'
        User = 'user:edit'
        UserFollows = 'user:edit:follows'
        UserReadBlocks = 'user:read:blocked_users'
        UserManageBlocks = 'user:manage:blocked_users'
        UserBroadcast = 'user:read:broadcast'
        UserEmail = 'user:read:email'

    def __init__(self, auth_info: dict, scopes: Optional[List[Scope]] = None):
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._refresh_token = None
        self._is_authenticated = False
        self._scopes = scopes

        access_token = auth_info.get('access_token')
        client_id = auth_info.get('client_id')
        client_secret = auth_info.get('client_secret')

        if access_token is not None:
            self._access_token = access_token
            self._client_id = self.validate_token(self._access_token)
            self._is_authenticated = self._client_id is not None

        elif client_id is not None and client_secret is not None:
            print('Attempting to get access token with provided client_id and client_secret...')
            self._client_id = client_id
            self._client_secret = client_secret

            try:
                self.__oauth()
            except ValueError as err:
                print(f'Could not authenticate: {err}')
                self._is_authenticated = False
            else:
                self._is_authenticated = True
        else:
            raise ValueError('Could not authtenticate with twitch, invalid credentials provided')

        if self._is_authenticated:
            print('Successfully authenticated with twitch.')
        else:
            print('Could not authenticate with twitch, invalid credentials.')


    def __oauth(self) -> None:
        params = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            }

        if self._scopes and len(self._scopes) > 0:
            params['scopes'] = ' '.join(self._scopes)

        if self._refresh_token is not None:
            '''
            Check https://dev.twitch.tv/docs/authentication#refreshing-access-tokens for more details
            '''
            params['refresh_token'] = self._refresh_token
            params['grant_type'] = 'refresh_token'

            auth_res = requests.post(Twitch.APIURL.AuthToken.value, params = params)
            if auth_res.status_code != 200:
                raise ValueError('Invalid ClientID or ClientSecret')
        else:
            '''
            Need to get an access token using the authentication mechanisms from twitch.tv
            so that we can use the twitch.tv API to get stream information
            More details: https://dev.twitch.tv/docs/authentication/
            Specific mechanism used here: https://dev.twitch.tv/docs/authentication/getting-tokens-oauth#oauth-client-credentials-flow
            '''
            params['grant_type'] = 'client_credentials'
            auth_res = requests.post(Twitch.APIURL.AuthToken.value, params = params)

            if auth_res.status_code != 200:
                raise ValueError('Invalid ClientID or ClientSecret')

            auth_data = auth_res.json()
            self._access_token = auth_data.get('access_token')
            self._refresh_token = auth_data.get('refresh_token')

            if self._access_token is None:
                print('Could not retrieve twitch access token')



    def __validate_response(self, request_response: requests.Response) -> bool:
        sc = request_response.status_code

        if sc == 401:
            if request_response.headers['WWW-Authenticate'] == r"OAuth realm='TwitchTV', error='invalid_token":
                try:
                    self.__oauth()
                except ValueError:
                    print('Cannot validate user access')
                    return False

        elif sc != 200:
            print(f'Could not validate response, bad response {request_response.text}')
            return False

        return True



    def __attempt_request_get(self, url: str, **kwargs) -> Optional[requests.Response]:
        response = requests.get(url,
            headers = {
                'Client-ID'     : self._client_id,
                'Authorization' : f'Bearer {self._access_token}',
                },
                **kwargs
            )

        if self.__validate_response(response):
            return response



    def __attempt_request_post(self, url: str, **kwargs) -> Optional[requests.Response]:
        response = requests.post(url,
            headers = {
                'Client-ID'     : self._client_id,
                'Authorization' : f'Bearer {self._access_token}',
                },
                **kwargs
            )

        if self.__validate_response(response):
            return response



    @staticmethod
    def validate_token(access_token: str) -> Optional[str]:
        if not access_token:
            raise ValueError('No access_token given, cannot validate')

        response = requests.get(Twitch.APIURL.ValidateToken.value,
                headers = {
                    'Authorization' : f'OAuth {access_token}',
                    }
                )

        if response == 200:
            return response.json().get('client_id')

        return None



    @staticmethod
    def revoke_access(client_id: str, access_token: str) -> None:
        if not client_id:
            raise ValueError('Invalid client_id provided')

        if not access_token:
            raise ValueError('Invalid access_token provided')

        requests.post(Twitch.APIURL.RevokeToken.value,
            params = {
                'client_id' : client_id,
                'token'     : access_token,
                }
            )



    def revoke_my_access(self):
        Twitch.revoke_access(self._client_id, self._access_token)
        self._is_authenticated = False



    @property
    def authenticated(self):
        return self._is_authenticated



    @property
    def client_id(self):
        return self._client_id



    @property
    def access_token(self):
        return self._access_token



    def get_users_info(self, ids: List[str]) -> Optional[List[dict]]:
        '''
        Check https://dev.twitch.tv/docs/api/reference#get-users for more details
        '''
        n = len(ids)

        if n > Twitch.Limits.UserRequests.value:
            raise ValueError(f'Requesting too many ids ({n}). Please reduce below {Twitch.Limits.UserRequests.value}')

        payload = []

        for id in ids:
            if id.isdecimal():
                payload.append(('id', id))
            else:
                payload.append(('login', id))

        print(f'Getting user request with payload: {payload}')

        response = self.__attempt_request_get(Twitch.APIURL.Users.value, params = payload)

        if response is not None:
            return response.json().get('data', [])
        else:
            print(f'There was an error with the get_users_info request. Payload {payload}')



    def get_user_info(self, user: Union[int, str]) -> Optional[dict]:
        info = self.get_users_info([user])

        if info and len(info) == 1:
            return info[0]

        return None



    def get_channel_info(self, user_id: str) -> Optional[dict]:
        response = self.__attempt_request_get(Twitch.APIURL.Channels.value, params = {'broadcaster_id': user_id})

        if response is None:
            return None

        res_json = response.json()

        data = res_json.get('data')

        if data is None or len(data) == 0:
            return None

        return data[0]



    def get_videos_info(self, video_ids: Optional[List[str]] = None, user_id: Optional[str] = None, game_id: Optional[str] = None, **kwargs: dict) -> Optional[Tuple[List[dict], str]]:
        # We need at least one of these to exist
        if all (v is None for v in {video_ids, user_id, game_id}):
            raise ValueError('Expected any combination of video_ids, user_id, or game_id to be specified')

        payload = []

        if video_ids:
            if len(video_ids) > Twitch.Limits.VideoRequests.value:
                raise ValueError(f'Requested too many video ids ({len(video_ids)}), please reduce to {Twitch.Limits.VideoRequests.value} or less')

            for id in video_ids:
                payload.append(('id', id))

        if user_id:
            payload.append(('user_id', user_id))

        if game_id:
            payload.append(('game_id', game_id))

        response = self.__attempt_request_get(Twitch.APIURL.Videos.value, params = payload, **kwargs)

        if response is None:
            return None

        res_json = response.json()

        video_data = res_json.get('data', [])
        pagination = res_json.get('pagination', {}).get('cursor')

        if len(video_data) == 0:
            return None

        return (video_data, pagination)



    def get_games_info(self, games: List[str]) -> Optional[List[dict]]:
        payload = []
        
        if len(games) > Twitch.Limits.GamesRequests.value:
            raise ValueError(f'Requested too many game ids ({len(games)}), please reduce to {Twitch.Limits.GamesRequests.value} or less')

        for id in games:
            if id.isdecimal():
                payload.append(('id', id))
            else:
                payload.append(('name', id))

        response = self.__attempt_request_get(Twitch.APIURL.Games.value, params = payload)

        if response is None:
            return None

        res_json = response.json()

        data = res_json.get('data', [])

        if len(data) == 0:
            return None

        return data



    def get_game_info(self, game: str) -> Optional[dict]:
        data = self.get_games_info([game])

        if data is None or len(data) == 0:
            return None

        return data[0]