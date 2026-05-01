<h1 align="center">
  <img alt="postarr logo" src=".github/images/postarr-logo-512.png" width="160px"/><br/>
  postarr
</h1>

<p align="center">Transform your Plex library with beautifully matched custom posters</p>

<p align="center"><img alt="GitHub activity" src="https://img.shields.io/github/last-commit/zarskie/postarr/develop?style=for-the-badge">&nbsp;<img alt="GitHub tags (latest by date)" src="https://img.shields.io/github/v/tag/zarskie/postarr?style=for-the-badge">&nbsp;<img alt="Build status" src="https://img.shields.io/github/actions/workflow/status/zarskie/postarr/docker-build-nightly.yml?style=for-the-badge">&nbsp;</p>

<p align="center"><img alt="postarr ui" src=".github/images/postarr-ui.png" /></p>

## Table of Contents

1. [What Is Postarr?](#what-is-postarr)
2. [Key Features](#key-features)
3. [Installation](#installation)
   - [Docker Compose](#docker-compose)
4. [Setup](#setup)
   - [RClone Configuration](#rclone-configuration)
   - [Setting up Plex, Radarr, & Sonarr](#setting-up-plex-radarr--sonarr)
   - [Configuring the modules](#configuring-the-modules)
     - [Drive Sync](#drive-sync)
     - [Postarr Renamerr](#postarr-renamerr)
     - [Plex Uploaderr](#plex-uploaderr)
     - [Unmatched Assets](#unmatched-assets)
   - [Webhook Setup](#webhook-setup)
   - [Schedule](#schedule)
5. [Community](#community)
6. [Contributing](#contributing)
   - [Bug Reports and Feature Requests](#bug-reports-and-feature-requests)
7. [Acknowledgements](#acknowledgements)

## What Is Postarr?

Postarr syncs poster files from any Google Drive (referred to throughout as G-Drive), matches them with your Plex media items, renames them to a specific naming scheme and uploads them to your Plex server.

## Key Features

- Sync posters from any G-Drive or community drives with RClone [Wiki](https://github.com/Drazzilb08/daps/wiki/rclone-configuration).
- Match and rename poster files to your Plex library using Kometa's naming scheme (Kometa itself is not required).
- Apply custom borders to posters — black, a custom hex color, or remove existing borders entirely.
- Upload matched poster files to Plex automatically.
- Webhook support with Radarr and Sonarr to upload posters as soon as new media is added [Wiki](https://github.com/zarskie/postarr/wiki/Webhook-Run).
- Automatically removes Kometa overlay labels when uploading new posters.
- Track movie editions — Postarr knows which edition of a film has had a poster applied.
- Match media using alternate titles from Radarr and Sonarr for hard-to-match items.
- Display unmatched assets and track poster coverage by percentage across movies, shows, seasons, and collections.
- Search drive folders directly in the UI with thumbnail previews.
- Schedule each module independently using cron syntax.
- View a complete job history and audit trail of all runs.

## Installation

Currently only docker is supported (may provide other installation methods down the road).

### Docker Compose

Modify accordingly if running with Unraid or other methods.

- MAIN_LOG_LEVEL is optional.
- Host port mapping might need to be changed to not collide with other apps.
- Change `BASE_DOCKER_DATA_PATH` to match your setup (e.g. `/mnt/user/appdata`).
- Set custom network if needed.
- Set ENV variables PUID and PGID to have postarr run as a specific user/group (default is `1000:1000`).

Create `docker-compose.yml` and add the following. If you have an existing setup change to fit that.

```yml

services:
  postarr:
    container_name: postarr
    image: ghcr.io/zarskie/postarr:develop
    restart: unless-stopped
    environment:
      - TZ=${TZ}
      - PUID=${PUID}
      - PGID=${PGID}
      - MAIN_LOG_LEVEL=INFO
    volumes:
      - ${BASE_DOCKER_DATA_PATH}/postarr/config:/config
      - /path/to/drive/folders:/posters
      - /path/to/asset/folder:/assets
    ports:
      - 8000:8000
```

Then start with:

```bash
docker compose up -d
```

> **Backup note:** Postarr stores all matched poster state in a SQLite database at `/config/db/database.db` inside the container. Make sure your `/config` volume is included in any backup routine — losing this file means Postarr will need to re-match and re-upload everything from scratch.

### Environment Variables

The following environment variables can be used:

| Variable                               | Description                                              | Default                                  |
|----------------------------------------|----------------------------------------------------------|------------------------------------------|
| `MAIN_LOG_LEVEL`                       | Web UI Log Level                                                           | `INFO`                 |
| `TIME_FORMAT`                          | Time format (12/24)                                                        | `12`                   |
| `PUID`                                 | User to run as                                                             | `1000`                 |
| `PGID`                                 | Group to run as                                                            | `1000`                 |
| `MAX_LOG_SIZE_MB`                      | Max log size (mb)                                                          | `25`                   |
| `MAX_BACKUP_FILES`                     | Max number of rotating logs                                                | `10`                   |
| `WEBHOOK_INITIAL_DELAY`                | Initial delay (seconds) before searching plex on webhook run               | `0`                    |
| `WEBHOOK_RETRY_DELAY`                  | Delay (seconds) between each retry when searching for recently added items | `30`                   |
| `WEBHOOK_MAX_RETRIES`                  | Maximum number of search attempts before giving up                         | `10`                   |
| `APP_DATA_DIR`                         | Path to configuration directory inside the container                       | `/config`              |

## Setup

### RClone Configuration

RClone is used by the Drive Sync module to pull poster files from G-Drive to your local machine. Follow [these instructions](https://github.com/Drazzilb08/daps/wiki/rclone-configuration) from the DAPS wiki to set it up — those instructions also link to a guide for getting an RClone Client ID and Secret, which you'll need if using OAuth authentication.

### Setting up Plex, Radarr, & Sonarr

When you first launch the app, navigate to **Settings > Instances** to connect Plex, Radarr, and Sonarr. Each form field has placeholder text showing exactly what to enter.

You can find your Sonarr & Radarr API keys at **Settings > General > Security** in each app. For Plex, follow [this guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) to find your authentication token.

> **Important:** The instance names you set here must match *exactly* what you reference elsewhere in Postarr's settings (including capitalization). A mismatch here is a common source of broken matching.

### Configuring the modules

After setting up your Sonarr, Radarr, and Plex instances you can then navigate to Settings > Settings to configure the modules.  There are four modules that can be configured:

- **Drive Sync** — Syncs poster image files from G-Drive to a local folder using rclone. This is the starting point: it pulls community poster files down to your machine so the other modules can work with them.
- **Postarr Renamerr** — Matches poster files to items in your Plex library (via Radarr, Sonarr, and Plex) and renames them to a standardized naming scheme. It handles movies, TV series, seasons, and collections, and can optionally modify poster borders during this step.
- **Unmatched Assets** — Identifies which items in your Plex library don't yet have a matched poster. Use this to see gaps in your poster coverage and track progress over time.
- **Plex Uploaderr** — Takes the matched and renamed poster files and uploads them directly to Plex so they appear in your library. It supports webhook mode to automatically upload a poster as soon as new media is added.

While these are four individual modules, they work in concert: Drive Sync pulls files down, Renamerr matches and organizes them, Unmatched Assets shows you what's missing, and Plex Uploaderr gets them into Plex.

Let's go through the settings page for each module.

#### Drive Sync

Since Drive Sync is what populates your local poster library, it's the best place to start. This module uses RClone to sync poster files from G-Drive to a local folder — the local folder is where the other modules will look for poster files to match and upload to Plex.

**Step 1: Configure RClone**

Click "Edit Config" and fill in your authentication details. If you're using OAuth, select that and fill in your Client ID, Client Secret, and OAuth Token. If you're using a Service Account, enter the path to your service account JSON file. Note that this path is relative to the container — if your file is named `rclone_sa.json` and you placed it in the root of your Postarr config folder, you'd enter `/config/rclone_sa.json`.

**Step 2: Add G-Drives**

You'll start with no G-Drives configured. Click "Add G-Drive" to add your first one. Each G-Drive is a folder that contains poster files, and you can add as many as you want. Each artist's folder is prefixed with the style of posters it contains: either "CL2K" (Custom Legends 2K) or "MM2K" (Movie Mania 2K). Add whichever artist drives you want to sync.

**Step 3: Run your initial sync**

We recommend doing an initial sync before moving on. Depending on how many folders you added this may take a while, so it's worth following along in the logs. To kick it off, click the "Run Commands" banner at the bottom of the page, select "Drive Sync" from the dropdown, and click "Run Command". "Info" is fine for your log level, but feel free to select "Debug" or "Trace" if you want more detail. If there are any issues with your RClone config you'll find out quickly — the sync will fail and log an error.

#### Postarr Renamerr

Here is where you'll tell Postarr Renamerr about the artist folders that contain posters.  Firstly check either "mm2k", "cl2k", or "both" depending on which style(s) of posters you want.  Then click "Load Folders".  This will load all the folders you synced when setting up Drive Sync.  It is important to note that the folder order matters greatly here.  If you loaded both CL2K and MM2K folders and there is a poster for a particular film in both styles the CL2K one will be favored because it is alphabetically first.

> **Tip:** We recommend creating a folder in your `/posters` directory called `overrides`, manually adding it here, and placing it first in the list of folders.  If you ever prefer one poster over another for a particular film/series, copy it from the artist's folder into `overrides` and it will be favored over any other poster for that item — regardless of alphabetical order.

For the Library Names simply enter your Plex library names *exactly* as they appear in Plex.

You'll also need to choose an **Asset Folder Mode**. In flat mode, all renamed poster files are placed directly in your target directory (e.g. `MovieTitle.jpg`). In asset folder mode, each item gets its own subfolder (e.g. `MovieTitle/poster.jpg`). If you're also using Kometa, match whichever structure Kometa expects. Switching between modes mid-run is not supported — pick one and stick with it.

Lastly, check the actions you'd like to happen when Postarr Renamerr runs.  This is where you'd choose which other modules run alongside Postarr Renamerr.  For example if when Postarr Renamerr runs you want to ensure you have the latest set of posters from the artist's G-Drives select "Drive Sync" (note that this will add a minute or two of runtime as it has to sync the posters down before it can match and rename them).  If you want to automatically upload matched posters to Plex whenever Postarr Renamerr runs select "Plex Uploaderr".  This will ensure that any time you run Postarr Renamerr your Plex server is updated with the latest matched posters.  And if you want your posters to have a border select "Replace Border" and choose the "Border Type" from the dropdown below.

#### Plex Uploaderr

There's not much to configure here. The one notable option is "Reapply Posters" — when enabled, Plex Uploaderr will re-upload every matched poster to Plex on each run, even if it has already been applied before. Leave this off unless you need to force a full refresh.

#### Unmatched Assets

Two options here: "Show All Unmatched" includes items that exist in your Radarr/Sonarr libraries but have no media files yet (not just items missing a poster), and "Hide Collections" removes Plex collections from the unmatched list entirely if you don't want to track collection posters.

### Webhook Setup

For webhook setup instructions, see the [Webhook Run wiki entry](https://github.com/zarskie/Postarr/wiki/Webhook-Run).

### Schedule

Use the dropdown to select each module and then set the schedule using crontab syntax.  If you're not familiar with crontab syntax you can use [crontab.guru](https://crontab.guru) to generate the correct syntax from regular datetime syntax.

## Community

For support, join the friendly Trash Guides Community [TRaSH-Guides Discord](https://trash-guides.info/discord) and look for **Postarr** under community apps.

## Contributing

- If you want to contribute please reach out on the Trash Guides discord.
- If you want your drive added as a template please submit a pull request to the `develop` branch in the `drives.json` file.

### Bug Reports and Feature Requests

Please create a github issue.

## Acknowledgements

Postarr was inspired by and built on top of the work done in [DAPS](https://github.com/Drazzilb08/daps) by [Drazzilb08](https://github.com/Drazzilb08). Many thanks for laying the groundwork.

<br/>

Thanks to all contributors who have helped make Postarr better:

<a href="https://github.com/zarskie/postarr/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zarskie/postarr" />
</a>
