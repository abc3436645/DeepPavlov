"""
Copyright 2017 Neural Networks and Deep Learning lab, MIPT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sqlite3
from typing import List, Any, Dict, Optional, Generator, Tuple
from random import Random
from pathlib import Path

from overrides import overrides

from deeppavlov.core.common.log import get_logger
from deeppavlov.core.common.registry import register
from deeppavlov.core.data.utils import download
from deeppavlov.core.commands.utils import expand_path, is_empty
from deeppavlov.core.data.data_fitting_iterator import DataFittingIterator

logger = get_logger(__name__)


@register('sqlite_iterator')
class SQLiteDataIterator(DataFittingIterator):
    """
    Load a SQLite database, read data batches and get docs content.
    """

    def __init__(self, save_path: str = '', load_path: str=None, data_url: str=None,
                 batch_size: int = None, shuffle: bool = None, seed: int = None, **kwargs):
        """
        :param save_path: a directory name where DB is located
        :param load_path: a path to local SQLite DB
        :param data_url: an URL to SQLite DB
        :param batch_size: a batch size for reading from the database
        """
        if Path(load_path).is_file():
            download_path = load_path
        else:
            download_dir = expand_path(save_path)
            download_path = download_dir.joinpath(data_url.split("/")[-1])
            download(download_path, data_url, force_download=False)

        # if not download_dir.exists() or is_empty(download_dir):
        #     logger.info('[downloading wiki.db from {} to {}]'.format(data_url, download_path))
        #     download(download_path, data_url)

        self.connect = sqlite3.connect(str(download_path), check_same_thread=False)
        self.db_name = self.get_db_name()
        self.doc_ids = self.get_doc_ids()
        self.doc2index = self.map_doc2idx()
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.random = Random(seed)

    @overrides
    def get_doc_ids(self) -> List[Any]:
        cursor = self.connect.cursor()
        cursor.execute('SELECT id FROM {}'.format(self.db_name))
        ids = [ids[0] for ids in cursor.fetchall()]
        cursor.close()
        return ids

    def get_db_name(self) -> str:
        cursor = self.connect.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        assert cursor.arraysize == 1
        name = cursor.fetchone()[0]
        cursor.close()
        return name

    def map_doc2idx(self) -> Dict[int, Any]:
        doc2idx = {doc_id: i for i, doc_id in enumerate(self.doc_ids)}
        logger.info(
            "SQLite iterator: The size of the database is {} documents".format(len(doc2idx)))
        return doc2idx

    @overrides
    def get_doc_content(self, doc_id: Any) -> Optional[str]:
        cursor = self.connect.cursor()
        cursor.execute(
            "SELECT text FROM {} WHERE id = ?".format(self.db_name),
            (doc_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result if result is None else result[0]
