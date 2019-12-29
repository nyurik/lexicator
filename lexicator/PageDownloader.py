from lexicator.consts import re_template_names
from lexicator.wikicache.TemplateDownloader import TemplateDownloader
from lexicator.wikicache.utils import MwSite, LogConfig


class TemplateDownloaderRu(TemplateDownloader):
    def __init__(self, site: MwSite, log_config: LogConfig):
        super().__init__(site=site, title_filter=self.title_filter, log_config=log_config)

    # noinspection PyUnusedLocal
    @staticmethod
    def title_filter(ns: int, title: str):
        return re_template_names.match(title) or title
