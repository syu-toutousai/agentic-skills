class MediaRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, media_type):
        def wrapper(wrapped_class):
            cls._registry[media_type] = wrapped_class
            return wrapped_class
        return wrapper

    @classmethod
    def get_media_class(cls, media_type):
        return cls._registry.get(media_type)

class MediaBase:
    def __init__(self, media_id, title):
        self.media_id = media_id
        self.title = title
    
    def get_embed_url(self, *args, **kwargs):
        raise NotImplementedError

@MediaRegistry.register("anime")
class AnimeMedia(MediaBase):
    def get_embed_url(self, episode=1, sub_or_dub="sub", **kwargs):
        return f"https://vidnest.fun/anime/{self.media_id}/{episode}/{sub_or_dub}"

@MediaRegistry.register("movie")
class MovieMedia(MediaBase):
    def get_embed_url(self, **kwargs):
        return f"https://vidsrc.to/embed/movie/{self.media_id}"

@MediaRegistry.register("tv")
class TVMedia(MediaBase):
    def get_embed_url(self, season=1, episode=1, **kwargs):
        return f"https://vidsrc.to/embed/tv/{self.media_id}/{season}/{episode}"

@MediaRegistry.register("radio")
class RadioMedia(MediaBase):
    def get_embed_url(self, **kwargs):
        js = f"var a=document.createElement('audio');a.controls=true;a.autoplay=true;a.style.width='100%';a.src='{self.media_id}';this.parentNode.replaceChild(a,this);"
        return f'<img src="x" onerror="{js}" />'

@MediaRegistry.register("podcast")
class PodcastMedia(MediaBase):
    def get_embed_url(self, **kwargs):
        return f"https://embed.podcasts.apple.com/us/podcast/id{self.media_id}"

@MediaRegistry.register("soundcloud")
class SoundcloudMedia(MediaBase):
    def get_embed_url(self, **kwargs):
        return f"https://w.soundcloud.com/player/?url={self.media_id}"

@MediaRegistry.register("manga")
class MangaMedia(MediaBase):
    def get_embed_url(self, cover_url="", synopsis="", **kwargs):
        return f'![Cover Art]({cover_url})\n\n{synopsis}'
