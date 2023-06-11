import obspython as obs
import json

from typing import Tuple, List, Optional, Union, Callable
from pathlib import Path
from abc import ABC, abstractmethod

from pytwitch.twitch import Twitch
from discordwebhooks.webhook import DiscordWebhook, DiscordEmbed


# Constants
BOXART_RATIO = 13/18


class NotAuthenticatedError(Exception):
    def __init__(self, message):
        super().__init__(message)


class OBSScript(ABC):
    frontend_event_callbacks = {}
    
    @staticmethod
    def handle_events(event) -> None:
        event_callbacks = OBSScript.frontend_event_callbacks.get(event, [])

        for callback in event_callbacks:
            callback()

    @staticmethod
    def register_frontend_event_callback(event, callback: Callable) -> None:
        print(f'Registering callback {callback} for event {event}')
        event_callbacks = OBSScript.frontend_event_callbacks.setdefault(event, [])
        event_callbacks.append(callback)

    @abstractmethod
    def on_loaded(self, settings) -> None:
        pass

    @abstractmethod
    def on_unloaded(self) -> None:
        pass

    @abstractmethod
    def on_saved(self, settings) -> None:
        pass

    @abstractmethod
    def define_properties(self):
        pass

    @abstractmethod
    def set_property_defaults(self, settings) -> None:
        pass

    @abstractmethod
    def on_properties_updated(self, settings) -> None:
        pass

    @abstractmethod
    def description(self) -> str:
        pass


class DiscordNotificationScript(OBSScript):
    def __init__(self):
        self._discord_start_msg = None
        self._discord_stop_msg = None
        self._twitter_start_msg_lines = []
        self._twitter_stop_msg_lines = []
        self._username = None
        self._boxart_height  = 72
        self._twitch_auth_path = Path()
        self._twitter_auth_path = Path()
        self._hooks_list = []
        self._twitch = None
        self._is_streaming = False
        self._tweepy_api = None
        self._user_id = None
        self._loaded = False
        self._do_discord_start_notice = False
        self._do_discord_stop_notice = False
        self._do_twitter_start_notice = False
        self._do_twitter_stop_notice = False
        self._previous_selected_scene = None
        self._load_settings = None


    def __on_frontend_loaded(self) -> None:
        print('Frontend has loaded, attempting authentication')
        self.__attempt_authentication()
        self._loaded = True


    def __attempt_authentication(self, twitch: Optional[bool] = True) -> None:
        if twitch and self._twitch_auth_path is not None and self._twitch_auth_path.is_file() and (self._twitch is None or not self._twitch.authenticated):
            self.__authenticate_twitch()


    def __authenticate_twitch(self) -> None:
        print('Authenticating with twitch...')
        
        auth = None
        try:
            auth = load_json_file(self._twitch_auth_path)
        except ValueError as err:
            print(f'{err}')
        else:
            if auth is None:
                print(f'Invalid data in twitch auth file {self._twitch_auth_path.as_posix()}')
            else:
                self._twitch = Twitch(auth)

                if self._twitch.authenticated:
                    print('Twitch Authentication successful, access token acquired.')
                else:
                    self._twitch = None
                    print('Could not authenticate with twitch, please check your client_id, client_secret, or access_token are valid')


    def __unauthenticate_twitch(self) -> None:
        if self._twitch and self._twitch.authenticated:
            self._twitch.revoke_my_access()
          

    def __on_start(self) -> None:
        try:
            (name, title, game_name, _, boxart_url, width, height) = self.__get_relavent_channel_info()
        except (ValueError, NotAuthenticatedError) as err:
            print(f'Can not retrieve channel information: {err}')
        else:
            title = f'{name} is streaming {game_name} on twitch.tv  | {title}'
            stream_url = fr'https://www.twitch.tv/{self._username}/'

            if self._do_discord_start_notice:
                embed = DiscordEmbed(
                    title = title,
                    url = stream_url,
                    image = {'url': boxart_url, 'width': width, 'height': height}
                )

                embed.set_timestamp('')

                DiscordWebhook.execute_on_urls(
                    [(url, None, None) for url in self._hooks_list],
                    self._discord_start_msg,
                    [embed])

        finally:
            self._is_streaming = True


    def __on_stop(self) -> None:
        if not self._twitch or not self._twitch.authenticated:
            raise NotAuthenticatedError('Not Authenticated with twitch, cannot retrieve information')

        user_info = self._twitch.get_user_info(self._username)
        if user_info is None:
            raise ValueError('Invalid twitch username')

        user_id = user_info.get('id')

        (video_info, _) = self._twitch.get_videos_info(user_id = user_id)

        if video_info is None or len(video_info) == 0:
            raise ValueError('Invalid video info requested')

        video = video_info[0]
        video_url = video.get('url', '')

        if self._do_discord_stop_notice:
            embed = DiscordEmbed(
                title = video.get('title', ''),
                url = video_url
            )

            embed.set_timestamp('')
            DiscordWebhook.execute_on_urls(
                [(url, None, None) for url in self._hooks_list],
                self._discord_stop_msg,
                [embed])

        self._is_streaming = False


    def __on_scene_changed(self) -> None:
        pass


    def __get_relavent_channel_info(self, user_id: Optional[str] = None) -> Tuple[str, str, str, str, str, int, int]:
        if not self._twitch.authenticated:
            raise NotAuthenticatedError('Cannot retrieve channel information, not authenticated with twitch.')

        if not user_id:
            user_info = self._twitch.get_user_info(self._username)

            if user_info is None:
                raise ValueError('Invalid twitch username')

            user_id = user_info.get('id')

        channel_info = self._twitch.get_channel_info(user_id)

        if channel_info is None:
            raise ValueError('Invalid user id')

        game_name = channel_info['game_name']
        game_id = channel_info['game_id']
        title = channel_info['title']
        name = channel_info['broadcaster_name']

        game_info = self._twitch.get_game_info(game_id) or {}

        width = int(round(self._boxart_height * BOXART_RATIO))
        height = int(self._boxart_height)
        boxart_url = game_info.get('box_art_url', '').replace(r'{width}x{height}', f'{width}x{height}')

        return (name, title, game_name, game_id, boxart_url, width, height)



    def on_loaded(self, settings) -> None:
        OBSScript.register_frontend_event_callback(obs.OBS_FRONTEND_EVENT_FINISHED_LOADING, self.__on_frontend_loaded)
        OBSScript.register_frontend_event_callback(obs.OBS_FRONTEND_EVENT_EXIT, self.__unauthenticate_twitch)
        OBSScript.register_frontend_event_callback(obs.OBS_FRONTEND_EVENT_SCENE_CHANGED, self.__on_scene_changed)
        OBSScript.register_frontend_event_callback(obs.OBS_FRONTEND_EVENT_STREAMING_STARTED, self.__on_start)
        OBSScript.register_frontend_event_callback(obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED, self.__on_stop)

    

    def on_unloaded(self) -> None:
        self.__unauthenticate_twitch()



    def on_saved(self, settings) -> None:
        pass



    def description(self) -> str:
        return 'Posts a notification that the stream is starting to all given discord webhook urls, and to a given twitter account.'



    def define_properties(self):
        print('Script properties defined.')
        props = obs.obs_properties_create()
        twitch_group = obs.obs_properties_create()
        discord_group = obs.obs_properties_create()

        discord_start_msg_group = obs.obs_properties_create()
        discord_stop_msg_group = obs.obs_properties_create()


        obs.obs_properties_add_group(props, 'twitch_group', 'Twitch Information', obs.OBS_GROUP_NORMAL, twitch_group)
        obs.obs_properties_add_text(twitch_group, 'username', 'Twitch Username', obs.OBS_TEXT_DEFAULT)
        obs.obs_properties_add_path(twitch_group, 'twitch_auth_path', 'Twitch Auth File', obs.OBS_PATH_FILE_SAVE, '*.json', '')

        obs.obs_properties_add_group(props, 'discord_group', 'Discord Information', obs.OBS_GROUP_NORMAL, discord_group)
        obs.obs_properties_add_int(discord_group, 'boxart_height', 'Boxart Height', 480, 4000, 100)
        obs.obs_properties_add_group(discord_group, 'discord_do_start', 'Enable Discord Start Msg', obs.OBS_GROUP_CHECKABLE, discord_start_msg_group)
        obs.obs_properties_add_text(discord_start_msg_group, 'discord_start_msg_x', 'Discord Start Message', obs.OBS_TEXT_DEFAULT)

        obs.obs_properties_add_group(discord_group, 'discord_do_stop', 'Enable Discord Stop Msg', obs.OBS_GROUP_CHECKABLE, discord_stop_msg_group)
        obs.obs_properties_add_text(discord_stop_msg_group, 'discord_stop_msg', 'Discord Stop Message', obs.OBS_TEXT_DEFAULT)

        obs.obs_properties_add_editable_list(discord_group, 'hook_urls_list', 'Discord Hook URLs', obs.OBS_EDITABLE_LIST_TYPE_STRINGS, '', '')

        return props



    def set_property_defaults(self, settings) -> None:
        obs.obs_data_set_default_string(settings, 'discord_start_msg', 'The stream has started, come watch!')
        obs.obs_data_set_default_string(settings, 'discord_stop_msg', 'The stream has ended. Go check out the VOD!')
        obs.obs_data_set_default_int(settings, 'boxart_height', 480)



    def on_properties_updated(self, settings) -> None:
        self._discord_start_msg = obs.obs_data_get_string(settings, 'discord_start_msg_x')
        self._discord_stop_msg = obs.obs_data_get_string(settings, 'discord_stop_msg')
        self._twitter_stop_msg = obs.obs_data_get_string(settings, 'twitter_stop_msg')
        self._username = obs.obs_data_get_string(settings, 'username')
        self._boxart_height = obs.obs_data_get_int(settings, 'boxart_height')
        twitch_auth_path = Path(obs.obs_data_get_string(settings, 'twitch_auth_path'))

        self._do_discord_start_notice = obs.obs_data_get_bool(settings, 'discord_do_start')
        self._do_discord_stop_notice = obs.obs_data_get_bool(settings, 'discord_do_stop')

        self._hooks_list = self.__obs_list_to_python_list(settings, 'hook_urls_list')

        authTwitch = False

        if twitch_auth_path != self._twitch_auth_path:
            self._twitch_auth_path = twitch_auth_path
            authTwitch = True

        if self._loaded:
            self.__attempt_authentication(authTwitch)



    def __obs_list_to_python_list(self, settings, property_name: str) -> List[str]:
        arr = []
        obs_list = obs.obs_data_get_array(settings, property_name)

        for i in range(obs.obs_data_array_count(obs_list)):
            item = obs.obs_data_array_item(obs_list, i)
            val = json.loads(obs.obs_data_get_json(item))
            arr.append(val.get('value'))
            obs.obs_data_release(item)

        obs.obs_data_array_release(obs_list)
        return arr



def load_json_file(file_path: Path) -> Optional[dict]:
    data = None

    if file_path is None:
        raise ValueError('Attempted to load a None json file')

    if not file_path.is_file():
        print(f'Tried to load invalid file {file_path.as_posix()}')
    else:
        try:
            with file_path.open('r') as f:
                data = json.load(f)
        except json.JSONDecodeError as err:
            print(f'There was an error loading twitter auth information from {file_path.as_posix()}: {err}')
        except FileNotFoundError:
            print(f'Could not find file {file_path.as_posix()}')
        except Exception as err:
            print(f'There was an error opening the file {file_path.as_posix()} --- {err}')

    return data



discord_script = DiscordNotificationScript()



def script_load(settings) -> None:
    global discord_script
    discord_script.on_loaded(settings)
    obs.obs_frontend_add_event_callback(DiscordNotificationScript.handle_events)



def script_description() -> str:
    global discord_script
    return discord_script.description()



def script_properties():
    global discord_script
    return discord_script.define_properties()



def script_defaults(settings) -> None:
    global discord_script
    discord_script.set_property_defaults(settings)



def script_update(settings) -> None:
    global discord_script
    discord_script.on_properties_updated(settings)


def script_unload() -> None:
    global discord_script
    discord_script.on_unloaded()


def script_save(settings) -> None:
    global discord_script
    discord_script.on_saved(settings)