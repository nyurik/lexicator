import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Callable, Set, Union, TypeVar

from pywikiapi import to_timestamp
from sqlalchemy import Column, Integer, Unicode, UnicodeText, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .PageContent import PageContent
from .PageRetriever import PageRetriever
from .utils import batches, trim_timedelta

T = TypeVar('T')


def to_compact_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


class ContentStore:
    def __init__(self, filename: Path, retriever: PageRetriever):
        self.filename = filename
        self.retriever = retriever
        self.retriever_initialized = False

        self.engine = create_engine(f'sqlite:///{filename}',
                                    # echo=True
                                    )
        self.Base = declarative_base(bind=self.engine)

        class PageContentDb(self.Base):
            __tablename__ = 'pages'

            title = Column(Unicode(256), primary_key=True)
            timestamp = Column(DateTime, index=True, nullable=True)
            ns = Column(Integer, nullable=True)
            revid = Column(Integer, nullable=True)
            user = Column(Unicode(256), nullable=True)
            redirect = Column(Unicode(256), nullable=True)
            data = Column(UnicodeText, nullable=True)
            content = Column(UnicodeText, nullable=True)

            def __init__(self, content: PageContent) -> None:
                super().__init__(
                    title=content.title,
                    timestamp=content.timestamp,
                    ns=content.ns,
                    revid=content.revid,
                    user=content.user,
                    redirect=content.redirect,
                    data=to_compact_json(content.data) if content.data is not None else None,
                    content=content.content,
                )

            def to_content(self):
                return PageContent(
                    title=self.title,
                    timestamp=self.timestamp,
                    ns=self.ns,
                    revid=self.revid,
                    user=self.user,
                    redirect=self.redirect,
                    data=None if self.data is None else json.loads(self.data),
                    content=self.content,
                )

        class InfoDb(self.Base):
            __tablename__ = 'info'
            info_id = Column(Integer, primary_key=True, autoincrement=True)
            timestamp = Column(DateTime)

        self.Base.metadata.create_all()
        self.db = sessionmaker(bind=self.engine)()
        self.PageContentDb = PageContentDb
        self.InfoDb = InfoDb
        self.retriever_source: ContentStore = self.retriever.source

    def init_retriever(self):
        if not self.retriever_initialized:
            self.retriever.init()
            self.retriever_initialized = True

    def get(self, key: str, force=False) -> PageContent:
        results = list(self.get_multiple([key], force))
        if len(results) > 1:
            raise ValueError(f'Multiple pages for key = {key}')
        if not results or results[0].is_deleted():
            raise KeyError(key)
        return results[0]

    def get_multiple(self, keys: Iterable[str], force=False) -> Iterable[PageContent]:
        self.init_retriever()
        self_force = force
        if force and isinstance(force, bool):
            force = False
        if not self_force or (self.retriever.is_remote and self_force == 'local'):
            not_found: Set[str] = set()
            for batch in batches(keys, 500):
                keys_tried = set()
                keys_to_try = set(batch)
                redirect_keys = False
                while len(keys_to_try) > 0:
                    redirect_keys = set()
                    keys_tried.update(keys_to_try)
                    for raw_page in self.db.query(self.PageContentDb).filter(self.PageContentDb.title.in_(keys_to_try)):
                        keys_to_try.remove(raw_page.title)
                        if not raw_page.redirect or not self.retriever.follow_redirects:
                            yield raw_page.to_content()
                        else:
                            redirect_keys.add(raw_page.redirect)
                    not_found.update(keys_to_try)
                    keys_to_try = redirect_keys - keys_tried
                for key in redirect_keys:
                    print(f"Title {key} is a redirect loop")
                if len(not_found) > 10000:
                    yield from self.save_pages(self.retriever.get_titles(not_found, force))
                    not_found.clear()
            keys = not_found

        if keys:
            yield from (
                v for v in self.save_pages(self.retriever.get_titles(keys, force=force))
                if not v.redirect or not self.retriever.follow_redirects
            )

    def read_object(self, key: str) -> PageContent:
        return self.get_raw_object(key).to_content()

    def get_raw_object(self, key: str):
        for page in self.db.query(self.PageContentDb).filter(self.PageContentDb.title == key):
            return page
        raise KeyError(key)

    def save_pages(self, pages: Iterable[PageContent]) -> Iterable[PageContent]:
        result = []
        delete = []
        for batch in batches(pages, 200):
            new_pages = {}
            for v in batch:
                if v.is_deleted():
                    delete.append(v.title)
                else:
                    new_pages[v.title] = v
            for page in self.db.query(self.PageContentDb).filter(self.PageContentDb.title.in_(new_pages.keys())):
                new_page = new_pages.pop(page.title)
                page.title = new_page.title
                page.timestamp = new_page.timestamp
                page.ns = new_page.ns
                page.revid = new_page.revid
                page.user = new_page.user
                page.redirect = new_page.redirect
                page.data = to_compact_json(new_page.data) if new_page.data is not None else None
                page.content = new_page.content
                result.append(new_page)
            for new_page in new_pages.values():
                self.db.add(self.PageContentDb(new_page))
                result.append(new_page)
            self.db.commit()
        self.delete_pages(delete)
        return result

    def delete_pages(self, delete):
        for batch in batches(delete, 1000):
            self.db.execute(self.PageContentDb.__table__.delete().where(self.PageContentDb.title.in_(batch)))
            self.db.commit()

    def store_object(self, value: PageContent) -> None:
        self.save_pages([value])

    def refresh(self, filters=None, delta: Union[timedelta, bool] = False) -> Iterable[str]:
        return self._track_progress(self.refresher, filters, delta)

    def refresher(self, progress, reporter, filters, delta: Union[timedelta, bool] = False) -> Iterable[str]:
        if not self.can_refresh():
            raise ValueError(f"Unable to refresh {self.filename}")

        # start_ts = datetime.utcnow()
        self.init_retriever()
        last_change = self.get_last_change()
        if delta:
            if isinstance(delta, timedelta):
                last_change -= delta
            else:
                last_change = None
        if self.retriever_source and last_change:
            ret_ts = self.retriever_source.get_last_change()
            if last_change >= ret_ts:
                print(f"Skipping {self.filename} refresh, underlying timestamp same as current source")
                return []

        if last_change and (datetime.utcnow() - last_change < timedelta(minutes=1)):
            print(f"Skipping {self.filename} refresh, underlying timestamp has not changed in last minute")
            return []

        # existing_keys, source = self.get_filters(last_change, refresh_type, reporter, start_ts, filters)
        source, delete = self.get_refresh_source(last_change, reporter, filters)

        titles: Set[str] = set()
        for batch in batches(source, 500):
            self.save_pages(batch)
            for v in batch:
                if not v.is_deleted():
                    progress['saved'] += 1
                    if v.timestamp and (not last_change or v.timestamp > last_change):
                        last_change = v.timestamp
                    titles.add(v.title)

        if delete:
            self.delete_pages(delete)
            print(f"Removed {len(delete):,} items from {self.filename}")

        if self.retriever_source:
            self.set_last_change(self.retriever_source.get_last_change())
        else:
            self.set_last_change(last_change - timedelta(minutes=5))

        return titles

    def get_refresh_source(self, last_change, reporter, filters):
        delete = []
        if not last_change or self.retriever.source:
            existing = self.get_stored_titles(self.db, self.PageContentDb, filters)
            if self.retriever_source:
                if last_change:
                    filters = [self.retriever_source.PageContentDb.timestamp > last_change, *(filters or [])]
                available = self.get_stored_titles(
                    self.retriever_source.db, self.retriever_source.PageContentDb, filters)
                source = self.retriever.get_titles(
                    {k: available[k] for k in available if k not in existing or existing[k] < available[k]},
                    force=False,
                    progress_reporter=reporter)
                if not last_change and not filters:
                    delete = {k for k in existing if k not in available}
                msg = f"Refreshing {self.filename} from underlying source. Last change at {last_change}, "
                if last_change:
                    msg += f"catching up {trim_timedelta(datetime.utcnow() - last_change)}"
                else:
                    msg += f"full refresh"
            else:
                print(f"Store {self.filename} has no last timestamp, forcing full reload")
                source = self.retriever.get_all_titles(reporter, existing, filters)
        else:
            source = self.retriever.get_titles(
                (v[0] for v in self.retriever.find_recent_changes(last_change - timedelta(seconds=5))),
                force=False,
                progress_reporter=reporter)
            print(f"Refreshing {self.filename} with the new changes. Last change at {last_change}, "
                  f"catching up {trim_timedelta(datetime.utcnow() - last_change)}")

        return source, delete

    @staticmethod
    def get_stored_titles(db, obj_type, filters):
        query = db.query(obj_type).filter(obj_type.timestamp is not None)
        if filters:
            query = query.filter(*filters)
        query = query.with_entities(obj_type.title, obj_type.timestamp)
        return {p[0]: p[1] for p in query}

    def get_last_change(self):
        try:
            for info in self.db.query(self.InfoDb):
                return info.timestamp
        except KeyError:
            return None

    def set_last_change(self, last_change: datetime):
        for info in self.db.query(self.InfoDb):
            info.timestamp = last_change
            self.db.commit()
            return
        info = self.InfoDb(timestamp=last_change)
        self.db.add(info)
        self.db.commit()

    def get_all(self, filters=None, order_by=None, columns=None) -> Iterable[PageContent]:
        query = self.db.query(self.PageContentDb)
        if filters is not None:
            if not isinstance(filters, list):
                filters = [filters]
            query = query.filter(*filters)
        if order_by is not None:
            if not isinstance(order_by, list):
                order_by = [order_by]
            query = query.order_by(*order_by)
        if columns is not None:
            if not isinstance(columns, list):
                columns = [columns]
            yield from query.with_entities(*columns)
        else:
            yield from (v.to_content() for v in query)

    def dump_to_file(self, filename: Path,
                     page_filter: Callable[[PageContent], bool] = None,
                     transform: Callable[[dict], Iterable[dict]] = None):
        with filename.open("w+", encoding='utf-8') as file:
            for page in self.get_all():
                if not page_filter or page_filter(page):
                    page_dict = page.to_dict()
                    try:
                        page_dict['timestamp'] = to_timestamp(page_dict['timestamp'])
                    except KeyError:
                        pass
                    if transform:
                        for val in transform(page_dict):
                            print(json.dumps(val, ensure_ascii=False, separators=(',', ':')), file=file)
                    else:
                        print(json.dumps(page_dict, ensure_ascii=False, separators=(',', ':')), file=file)

    def _track_progress(self, func: Callable[..., T], *args) -> T:
        start_ts = datetime.utcnow()
        processed = 0
        progress = {'saved': 0}
        last_report_ts = start_ts

        def reporter(title):
            nonlocal last_report_ts, processed
            processed += 1
            if processed % 100 == 0 and (datetime.utcnow() - last_report_ts).total_seconds() >= 15:
                last_report_ts = datetime.utcnow()
                seconds = (last_report_ts - start_ts).total_seconds()
                print(f"Processed {processed:,} and saved {progress['saved']:,} items "
                      f"in {trim_timedelta(last_report_ts - start_ts)}. "
                      f"Processing speed {int(processed / seconds):,}, "
                      f"save speed {int(progress['saved'] / seconds):,} items/s. "
                      f"Current item is '{title}'")

        result = func(progress, reporter, *args)

        now = datetime.utcnow()
        print(f"Finished refreshing {self.filename}: {progress['saved']:,} pages in {trim_timedelta(now - start_ts)}")

        return result

    def can_refresh(self) -> bool:
        return self.retriever.can_refresh()

    def custom_refresh(self, filters=None):
        for _ in self.get_multiple(self.retriever.custom_refresh(filters)):
            pass
