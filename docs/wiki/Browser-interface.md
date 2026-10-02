# Browser interface

The browser interface is the same tool as the command line, for **one person**, behind a
**password**, on a **LAN or VPN**. It edits the same assay files, runs the same command, writes
the same evaluation records and shows the same reports. Nothing it does is unavailable from the
command line, and nothing it writes differs from what the command line writes.

## Setting it up (Docker, e.g. on a NAS)

```bash
# once, in the folder with docker-compose.yml and work/
echo "QAC_UID=$(id -u)" >> .env; echo "QAC_GID=$(id -g)" >> .env   # run as the owner of work/
echo "QAC_PORT=8880" >> .env        # optional: another port when 8080 is taken
docker compose build
docker compose run --rm gui gui set-password --work /work
docker compose up -d
```

Open `http://<host>:8080` (or the `QAC_PORT` you chose). `NCBI_EMAIL` and `NCBI_API_KEY` go in
the same `.env`. After a `git pull`, run `docker compose build` and `docker compose up -d` again:
the container runs the code built into the image.

**Do not forward the port from the internet.** For access from outside, use a VPN. Behind an
HTTPS reverse proxy, start it with `--secure-cookie`.

## What is where

| Page | What it does | Files |
|---|---|---|
| Dashboard | latest record per assay, the run in progress, the queue, recent records | reads `work/results/` |
| Assays | list, new from the template, copy an example, edit (form or YAML), check as you type, QC only | `work/assays/`, history in `.history/`, deleted files in `.deleted/` |
| New run | choose an assay; see what would be sent to NCBI; confirm and queue | copies the confirmed file to `work/gui/jobs/<run>/` |
| Runs | the queue, each run's stages, count, live log; cancel; start again | logs in `work/runs/` |
| Results | every record per assay; the report in the page; downloads | reads `work/results/` |
| Settings | password, configuration file, NCBI environment, storage | `work/gui/auth.json`, `work/config.yaml`, history in `work/gui/history/` |

## How a run from the browser works

1. **Plan.** The page shows the oligo sequences that would be sent to NCBI's public servers and
   every planned BLAST search per tier: the plan `--dry-run` shows. The exclusivity tier's
   organism names are resolved when the run starts, as on the command line.
2. **Confirm.** The assay file is copied exactly as confirmed. If the file changed after the
   plan was shown, the GUI asks to plan again, so what was confirmed is what runs.
3. **Queue.** One run at a time. Each run is `qpcr-assay-check run <assay> -o work/results
   --yes -v` in its own process; `--yes` stands for the confirmation given in the browser.
4. **Follow.** The run page reads the stages and the latest count from the log as it grows.
5. **Stop or continue.** Cancel stops a run as Ctrl-C would. A cancelled, failed or interrupted
   run continues where it was when started again: stored genomes and finished searches are
   reused, unfinished searches resume.

Runs started with `scripts/run_assay.sh` share the cache and the records, but not the queue:
do not start one there while the GUI runs one.

## Security in short

- One password, stored only as a salted scrypt hash; the GUI does not start without it.
- After three wrong attempts, each further one from the same address waits longer (up to five
  minutes); failures are logged.
- Signed session cookie that scripts cannot read and other sites cannot send; signed out after
  8 hours without activity; a new password ends every other session at once.
- Every form carries a token checked on submit.
- The pages load nothing from elsewhere (fonts and styles ship with the package).
- The report is shown in a locked frame: no scripts, nothing from elsewhere, no access to the
  session; links open in a new tab. Only four files of a record can be downloaded.
- File and folder names in addresses are checked and must lie inside their folder.
- The NCBI email and API key stay in the environment; the GUI shows only whether they are set.

The laboratory verifies this software, the browser interface included, within its own quality
system. In silico analysis does not replace experimental validation.
