# BookFusion AutoSync for calibre

Add a book to the **BookFusion** shelf in Calibre-Web and, a few minutes later, calibre uploads it to BookFusion
using the official BookFusion plugin. No forks of Calibre-Web or of the official plugin.

## How it works

1. Every 5 minutes (configurable), the plugin reads Calibre-Web's `app.db` (read-only) and gets the books on the
   configured shelf.
2. Books that don't have a `bookfusion` identifier yet are handed to the official plugin's workers
   (`CheckWorker` + `UploadManager`), exactly as if you had clicked "Sync selected books".
3. Once done, the book gets `bookfusion:<id>` among its identifiers (also visible in Calibre-Web).

A book can be on the BookFusion shelf and on any other shelf at the same time.

## Requirements

- calibre 6.2.1 or later, with the official **BookFusion** plugin installed and its API key configured.
- Calibre-Web using the same library, with local access to its `app.db`.
- calibre running (the plugin lives inside the GUI).

## Installation

```powershell
.\install.ps1
```

On other platforms: `calibre-customize -b plugin`.

Restart calibre. Settings are under *Preferences → Plugins → BookFusion AutoSync* or in the action's menu
(add it to the toolbar from *Preferences → Toolbars & menus*).

| Setting | Default |
|---|---|
| Calibre-Web app.db | `C:\Program Files\Calibre-Web\app.db` |
| Shelf | `BookFusion` |
| Interval | 5 min |
| Startup delay | 60 s |

## Menu

- **Sync now**: uploads the pending books on the shelf.
- **Resync the whole shelf**: goes through every book again (pushes changed metadata, retries failed books).

## Notes

- Removing a book from the shelf does **not** delete it from BookFusion.
- If a book fails 3 times, or has an unsupported format or size, it is not retried until calibre restarts or you
  run a full resync.
- Log: `<library>\bookfusion_sync.log`, lines tagged `[autosync]` (requires "Debug Logging" in the BookFusion plugin).
- The default `app.db` path is the one used by the Calibre-Web Windows installer. With Docker it usually lives in
  the config volume (`/config/app.db`); in that case point the setting at the volume path on the host.
- calibre and Calibre-Web must use the same library; otherwise the plugin does nothing and says so.

## License

GPL v3, same as the official BookFusion plugin, whose code is reused.
