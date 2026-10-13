__license__ = 'GPL v3'

# Reproduces the SyncWidget flow of the official BookFusion plugin (CheckWorker -> UploadManager)
# without any dialogs, so it can be triggered from a timer.

import os
import time
import traceback

from qt.core import QObject, QThread

from calibre_plugins.bookfusion_autosync.config import prefs
from calibre_plugins.bookfusion_autosync.shelf_source import read_shelf, same_path, ShelfError

# Failed attempts per book before giving up on it for the current calibre session
MAX_ATTEMPTS = 3
# A sync that hangs (e.g. a network request that never answers) is canceled after this long
STALL_TIMEOUT = 30 * 60


class AutoSyncRunner(QObject):
    def __init__(self, gui):
        QObject.__init__(self, gui)

        self.gui = gui
        self.running = False
        self.started_at = 0
        self.thread = None
        self.worker = None
        self.logger = None
        self.last_warning = None

        # In-memory state: reset when calibre restarts or on a full resync
        self.attempts = {}
        self.rejected = set()
        self.missing = set()

    # ---------------------------------------------------------------- entry points

    def run(self, full=False, manual=False):
        if self.running and time.monotonic() - self.started_at > STALL_TIMEOUT:
            self.log('Stalled: canceling')
            self.cancel()
            self.running = False
        if self.running:
            if manual:
                self.notify('A sync is already running')
            return

        try:
            self._run(full, manual)
        except ShelfError as e:
            self.warn(str(e))
        except Exception as e:
            traceback.print_exc()
            self.running = False
            self.warn('Unexpected error: {}'.format(e))

    def cancel(self):
        if self.running and self.worker is not None:
            self.worker.cancel()

    # ---------------------------------------------------------------- preparation

    def _run(self, full, manual):
        try:
            from calibre_plugins.bookfusion.config import prefs as bf_prefs
            from calibre_plugins.bookfusion.logger import Logger
        except ImportError:
            return self.warn('The official BookFusion plugin is not installed')

        if not bf_prefs['api_key']:
            return self.warn('The BookFusion plugin has no API key configured')

        library_path = self.gui.current_db.library_path
        shelf_found, shelf_ids, cw_library = read_shelf(prefs['app_db_path'], prefs['shelf_name'])

        if cw_library and not same_path(cw_library, library_path):
            return self.warn('The open library is not the Calibre-Web one ({})'.format(cw_library))
        if not shelf_found:
            return self.warn('Calibre-Web has no shelf named "{}"'.format(prefs['shelf_name']))

        self.last_warning = None

        if full:
            self.attempts.clear()
            self.rejected.clear()
            self.missing.clear()

        db = self.gui.current_db.new_api

        if not self.pending_ids(db, shelf_ids, full, include_unknown=True):
            if manual:
                self.notify('Nothing pending on shelf "{}"'.format(prefs['shelf_name']))
            return

        # Calibre-Web writes to metadata.db behind calibre's back, so the GUI cache does not see
        # its new books or metadata changes until it is reloaded.
        db.reload_from_db()
        self.gui.refresh_all()

        pending = self.pending_ids(db, shelf_ids, full, include_unknown=False)
        known = db.all_book_ids()
        self.missing.update(i for i in shelf_ids if i not in known)
        if not pending:
            if manual:
                self.notify('Nothing pending on shelf "{}"'.format(prefs['shelf_name']))
            return

        self.running = True
        self.started_at = time.monotonic()
        self.db = db
        self.pending = pending
        self.results = {'uploaded': [], 'updated': [], 'skipped': [], 'failed': {}, 'rejected': []}
        self.abort_msg = None
        self.logger = Logger(os.path.join(library_path, 'bookfusion_sync.log'))
        self.log('Start: full={}; book_ids={}'.format(full, pending))
        self.notify('Syncing {} book(s)...'.format(len(pending)))

        self.start_check()

    def pending_ids(self, db, shelf_ids, full, include_unknown):
        known = db.all_book_ids()
        pending = []
        for book_id in shelf_ids:
            if book_id in self.rejected or self.attempts.get(book_id, 0) >= MAX_ATTEMPTS:
                continue
            if book_id not in known:
                if include_unknown and book_id not in self.missing:
                    pending.append(book_id)
                continue
            if full or not db.field_for('identifiers', book_id).get('bookfusion'):
                pending.append(book_id)
        return pending

    # ---------------------------------------------------------------- check (limits, formats, size)

    def start_check(self):
        from calibre_plugins.bookfusion.check_worker import CheckWorker

        self.limits = {}
        self.valid_ids = None

        self.thread = QThread(self)
        self.worker = CheckWorker(self.db, self.logger, list(self.pending))
        self.worker.limitsAvailable.connect(self.on_limits)
        self.worker.resultsAvailable.connect(self.on_check_results)
        self.worker.aborted.connect(self.on_aborted)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.on_check_finished)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.start)
        self.thread.start()

    def on_limits(self, limits):
        self.limits = limits

    def on_check_results(self, books_count, valid_ids):
        self.valid_ids = valid_ids

    def on_aborted(self, msg):
        self.abort_msg = msg
        self.log('Aborted: {}'.format(msg))

    def on_check_finished(self):
        if not self.running:
            return
        if self.abort_msg or self.valid_ids is None:
            return self.finish()

        # Unsupported format or file too large: retrying makes no sense
        rejected = [i for i in self.pending if i not in self.valid_ids]
        self.rejected.update(rejected)
        self.results['rejected'] = rejected

        book_ids = list(self.valid_ids)
        if self.limits.get('total_books'):
            book_ids = book_ids[:self.limits['total_books']]
        if not book_ids:
            return self.finish()

        self.start_upload(book_ids)

    # ---------------------------------------------------------------- upload

    def start_upload(self, book_ids):
        from calibre_plugins.bookfusion.upload_manager import UploadManager

        self.thread = QThread(self)
        self.worker = UploadManager(self.db, self.logger, book_ids, False)
        self.worker.uploaded.connect(self.on_uploaded)
        self.worker.updated.connect(self.on_updated)
        self.worker.skipped.connect(self.on_skipped)
        self.worker.failed.connect(self.on_failed)
        self.worker.aborted.connect(self.on_aborted)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.on_upload_finished)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.start)
        self.thread.start()

    def on_uploaded(self, book_id):
        self.results['uploaded'].append(book_id)

    def on_updated(self, book_id):
        self.results['updated'].append(book_id)

    def on_skipped(self, book_id):
        self.results['skipped'].append(book_id)

    def on_failed(self, book_id, msg):
        self.results['failed'][book_id] = msg
        self.attempts[book_id] = self.attempts.get(book_id, 0) + 1

    def on_upload_finished(self):
        if not self.running:
            return

        done = self.results['uploaded'] + self.results['updated']
        if done:
            self.gui.library_view.model().refresh_ids(done)

        self.finish()

    # ---------------------------------------------------------------- wrap-up and notifications

    def finish(self):
        r = self.results
        parts = []
        if r['uploaded']:
            parts.append('{} uploaded'.format(len(r['uploaded'])))
        if r['updated']:
            parts.append('{} updated'.format(len(r['updated'])))
        if r['skipped']:
            parts.append('{} unchanged'.format(len(r['skipped'])))
        if r['failed']:
            parts.append('{} failed'.format(len(r['failed'])))
        if r['rejected']:
            parts.append('{} not supported (format or size)'.format(len(r['rejected'])))
        if self.abort_msg:
            parts.append('aborted: {}'.format(self.abort_msg))

        summary = ', '.join(parts) or 'no changes'
        self.log('Done: {}; failed={}; rejected={}'.format(summary, r['failed'], r['rejected']))
        self.notify(summary)

        self.running = False
        self.worker = None
        self.thread = None

    def log(self, msg):
        if self.logger is not None:
            self.logger.info('[autosync] {}'.format(msg))

    def notify(self, msg):
        msg = 'BookFusion AutoSync: {}'.format(msg)
        print(msg, flush=True)
        self.gui.status_bar.show_message(msg, 10000)

    def warn(self, msg):
        # Warnings repeat on every timer tick; only show them when they change
        if msg != self.last_warning:
            self.last_warning = msg
            self.notify(msg)
