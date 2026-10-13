__license__ = 'GPL v3'

# Reads Calibre-Web shelves straight from its app.db, always read-only:
# we never write to the Calibre-Web database.

import os
import sqlite3
from urllib.request import pathname2url


class ShelfError(Exception):
    pass


def read_shelf(app_db_path, shelf_name):
    '''
    Returns (shelf_found, book_ids, calibre_library_dir).

    If several users have a shelf with that name, all of them are merged.
    Name matching ignores case and surrounding whitespace.
    '''
    if not os.path.isfile(app_db_path):
        raise ShelfError('Calibre-Web database not found: {}'.format(app_db_path))

    target = shelf_name.strip().casefold()
    conn = sqlite3.connect('file:{}?mode=ro'.format(pathname2url(app_db_path)), uri=True, timeout=10)
    try:
        shelf_ids = [
            shelf_id for shelf_id, name in conn.execute('SELECT id, name FROM shelf')
            if (name or '').strip().casefold() == target
        ]

        book_ids = set()
        if shelf_ids:
            query = 'SELECT book_id FROM book_shelf_link WHERE shelf IN ({})'.format(','.join('?' * len(shelf_ids)))
            book_ids = {row[0] for row in conn.execute(query, shelf_ids)}

        row = conn.execute('SELECT config_calibre_dir FROM settings').fetchone()
    except sqlite3.Error as e:
        raise ShelfError('Error reading {}: {}'.format(app_db_path, e))
    finally:
        conn.close()

    return bool(shelf_ids), sorted(book_ids), (row[0] if row else None)


def same_path(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))
