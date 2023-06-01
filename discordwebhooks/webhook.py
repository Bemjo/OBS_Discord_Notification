import requests
from typing import List, Tuple, Optional, Union
from datetime import datetime
from enum import Enum

class DiscordEmbed:
    class Limits(int, Enum):
        """
        See https://discord.com/developers/docs/resources/channel#embed-limits for more details on these limits
        """
        TitleLength = 256
        DescriptionLength = 2048
        Fields = 25
        FieldNameLength = 256
        FieldValueLength = 1024
        FooterTextLength = 2048
        AuthorNameLength = 256
        # This limit is for title, description, field_names, field_values, footer_text, author_name
        MaxLength = 6000

    def __init__(self, **kwargs: dict):
        """
        See https://discord.com/developers/docs/resources/channel#embed-object for more details
        Excludes the type field, as it always has the value 'rich' for webhook embeds
        """
        self._title         = kwargs.get('title')
        self._description   = kwargs.get('description')
        self._url           = kwargs.get('url')
        self._timestamp     = kwargs.get('timestamp')
        self._color         = kwargs.get('color')
        self._footer        = kwargs.get('footer')
        self._image         = kwargs.get('image')
        self._thumbnail     = kwargs.get('thumbnail')
        self._video         = kwargs.get('video')
        self._provider      = kwargs.get('provider')
        self._author        = kwargs.get('author')
        self._fields        = kwargs.get('fields', [])



    def embed_length(self) -> int:
        length = 0

        length += len(self._title or '')
        length += len(self._description or '')

        if self._footer is not None:
            length += len(self._footer.get('text', ''))

        if self._author is not None:
            length += len(self._author.get('name', ''))

        # Create a list of field lengths for each field in this embed object
        if self._fields is not None:
            length += sum([len(x) + len(y) for f in self._fields for (x, y) in [f.get('name', ''), f.get('value', '')]])

        return length



    def is_embed_valid(self) -> bool:
        return (self.embed_length() <= DiscordEmbed.Limits.MaxLength) and not self.is_empty()



    def is_empty(self) -> bool:
        return all(v is None for v in [
                self._title,
                self._description,
                self._url,
                self._timestamp,
                self._color,
                self._footer,
                self._image,
                self._thumbnail,
                self._video,
                self._provider,
                self._author,
                self._fields,
                ])




    @property
    def title(self) -> Optional[str]:
        return self._title



    def set_title(self, title: Optional[str] = None) -> None:
        if title:
            title = title.strip()
            if len(title) > DiscordEmbed.Limits.TitleLength:
                raise ValueError('Embed title length is too long')

        self._title = title

    

    @property
    def description(self) -> Optional[str]:
        return self._description



    def set_description(self, description: Optional[str] = None) -> None:
        if description:
            description = description.strip()
            if len(description) > DiscordEmbed.Limits.DescriptionLength:
                raise ValueError('Embed description length is too long')
        self._description = description


    
    @property
    def url(self) -> Optional[str]:
        return self._url



    def set_url(self, url: Optional[str]) -> None:
        self._url = url



    @property
    def timestamp(self) -> Optional[str]:
        return self._timestamp



    def set_timestamp(self, timestamp: Optional[str] = None) -> None:
        '''
        timestamp should be an ISO8601 formatted date and time
        Will use the current date and time if it is not provided
        '''
        if timestamp is None:
            self._timestamp = None
        elif timestamp:
            self._timestamp = timestamp
        else:
            self._timestamp = datetime.now().astimezone().isoformat()


    
    @property
    def color(self) -> Optional[int]:
        return self._color



    def set_color_decimal(self, color: Optional[int]) -> None:
        self._color = color



    def set_color_rgb(self, r: int, g: int, b: int) -> None:
        if any(v > 255 for v in [r, g, b]):
            raise ValueError(f'Invalid rgb color given (r:{r}, g:{g}, b:{b}). Values must be 0 <= color <= 255')

        self._color = (r * 2**16) + (g * 2**8) + b



    def set_color_hex(self, hexcolor: str) -> None:
        hexcolor = hexcolor.replace('#', '')

        if len(hexcolor) > 6:
            raise ValueError('Hex color is invalid, must be 24 bits or no more than 6 hex characters')

        self._color = int(hexcolor.replace('#', ''), 16)



    @property
    def footer(self) -> Optional[str]:
        return self._footer



    def set_footer(self, footer: str) -> None:
        self._footer = footer.strip()



    @property
    def image(self) -> Optional[dict]:
        return self._image



    def set_image(self, url: str, proxy_url: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """
        Check https://discord.com/developers/docs/resources/channel#embed-object-embed-image-structure for more details
        """
        if not url:
            self._image = None
        else:
            self._image = {'url': url}

            if proxy_url:
                self._image['proxy_url'] = proxy_url
            if width:
                self._image['width'] = width
            if height:
                self._image['height'] = height



    @property
    def thumbnail(self) -> Optional[dict]:
        return self._thumbnail



    def set_thumbnail(self, url: str, proxy_url: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """
        Check https://discord.com/developers/docs/resources/channel#embed-object-embed-image-structure for more details
        """
        if not url:
            self.thumbnail = None
        else:
            self.thumbnail = {'url': url}

            if proxy_url:
                self.thumbnail['proxy_url'] = proxy_url
            if width:
                self.thumbnail['width'] = width
            if height:
                self.thumbnail['height'] = height



    @property
    def video(self) -> Optional[dict]:
        return self._video

    

    def set_video(self, url: str, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """
        Check https://discord.com/developers/docs/resources/channel#embed-object-embed-video-structure for more details
        """
        if not url:
            self._video = None
        else:
            self._video = {'url': url}

            if width:
                self._video['width'] = width
            if height:
                self._video['height'] = height



    @property
    def provider(self) -> Optional[dict]:
        return self._provider



    def set_provider(self, url: str, name: str) -> None:
        self._provider = {'url' : url, 'name': name}



    @property
    def author(self) -> Optional[dict]:
        return self._author


    
    def set_author(self, name: str, url: Optional[str], icon_url: Optional[str], proxy_icon_url: Optional[str]) -> None:
        self._author = {'name': name.strip()}

        if url:
            self._author['ur'] = url
        if icon_url:
            self._author['icon_url'] = icon_url
        if proxy_icon_url:
            self._author['proxy_icon_url'] = proxy_icon_url



    @property
    def fields(self) -> Optional[List[dict]]:
        return self._fields


    
    def add_field(self, name: str, value: str, inline: Optional[bool] = None) -> None:
        if len(self._fields) == DiscordEmbed.Limits.Fields:
            raise ValueError(f'Cannot add another field to embed, limit is {DiscordEmbed.Limits.Fields}')
        else:
            field = {'name': name.strip(), 'value': value.strip()}
            if inline is not None:
                field['inline'] = inline
            self._fields.append(field)



    @property
    def json(self) -> dict:
        data = {}

        if self._title:
            data['title'] = self._title
        if self._description:
            data['description'] = self._description
        if self._url:
            data['url'] = self._url
        if self._timestamp:
            data['timestamp'] = self._timestamp
        if self._color:
            data['color'] = self._color
        if self._footer:
            data['footer'] = self._footer
        if self.image:
            data['image'] = self._image
        if self._thumbnail:
            data['thumbnail'] = self._thumbnail
        if self._video:
            data['video'] = self._video
        if self._provider:
            data['provider'] = self._provider
        if self._author:
            data['author'] = self._author
        if self._fields:
            data['fields'] = self._fields

        return data



class DiscordWebhook:
    EMBED_LIMIT         = 10
    
    def __init__(self, urls: List[Tuple[str, Optional[str], Optional[str]]], content: Optional[str] = None, embeds: Optional[List[DiscordEmbed]] = []):
        """
        See https://discord.com/developers/docs/resources/webhook for more details
        Takes a list of (webhook_url, username override, avatar_url override) pairs.
        If username is empty or none, will use the default webhook username for the given url
        """

        self._urls = urls
        self._content = content
        self._embeds = embeds

        if len(self._urls) == 0:
            raise ValueError('Must include at least one webhook url')



    def __has_valid_message(self) -> bool:
        return (self._content is not None and len(self._content) > 0) or (self._embeds is not None and len(self._embeds) > 0)



    @property
    def content(self) -> Optional[str]:
        return self._content

    

    def set_content(self, content: Optional[str] = None) -> None:
        self._content = content


    
    @property
    def embeds(self) -> List[DiscordEmbed]:
        return self._embeds



    def add_embed(self, embed: DiscordEmbed) -> None:
        if len(self._embeds) == DiscordWebhook.EMBED_LIMIT:
            raise ValueError(f'Cannot add another embed, limit is {DiscordWebhook.EMBED_LIMIT}')
        if embed is None:
            raise ValueError('Attempted to add an embed of None')

        self._embeds.append(embed)



    def execute(self) -> None:
        if not self.__has_valid_message():
            raise ValueError('Did not define at least one of the content or embed field')

        for (url, username, avatar_url) in self._urls:
            self.__execute(url, username, avatar_url)



    def __execute(self, url: str, username: Optional[str] = None, avatar_url: Optional[str] = None) -> None:
        json_payload = {}

        if not self.__has_valid_message():
            raise ValueError('Cannot execute webhook, content or embeds were not defined.')
        
        if self._content:
            json_payload['content'] = self._content

        if self._embeds and len(self._embeds) > 0:
            json_payload['embeds'] = [x.json for x in self._embeds if x.is_embed_valid()]

        if username:
            json_payload['username'] = username

        if avatar_url:
            json_payload['avatar_url'] = avatar_url

        print(f'Webhook json_payload:\n{json_payload}')

        # Discord webhook details: https://discord.com/developers/docs/resources/webhook#execute-webhook
        hook_res = requests.post(url,
            headers = {'Content-Type' : 'application/json'},
            params = {'wait' : 'true'},
            json = json_payload
            )

        print(f'Webhook response: {hook_res.text}')
        
        if hook_res.status_code != 200:
            print(f'Error sending webhook. {hook_res.text}')



    @staticmethod
    def execute_on_urls(urls: List[Tuple[str, str, str]], content: Optional[str] = None, embeds: Optional[List[DiscordEmbed]] = []) -> None:
        """
        Executes a webhook with the provided content and embeds without having to create an object on your own
        """
        hook = DiscordWebhook(urls, content, embeds)
        hook.execute()