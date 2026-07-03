# Large artifacts — not in git

These are excluded by `.gitignore` because they exceed practical git/GitHub limits
(GitHub rejects files over 100 MB; several zips here are 150–320 MB).

## What is excluded

| What | Where | Size | Recoverable? |
|---|---|---|---|
| RVC voice models (`.zip`, `.pth`, `.index`) | `VoiceModels/` | ~5.3 GB | Yes — re-downloadable; record source URLs below |
| Stem zips from splitter | `silpama/audio/`, `bhashalu/audio/` | ~1.5 GB | Regenerable from source mp3s, but slow — back up |
| Video/image/wav renders | everywhere | ~15 GB | Regenerable via scripts + cue files |
| Reference PDFs | repo root | ~90 MB | Re-downloadable |

Final mp3 outputs and all text (lyrics, cue files, `.llc`, `.srt`, `.sbv`, scripts) stay in git.

## Backup target

Back up `VoiceModels/` and `*/audio/*.zip` outside git, e.g.:

```sh
# external drive
rsync -av --include='*/' --include='*.zip' --include='*.pth' --include='*.index' \
      --exclude='*' . /Volumes/BACKUP/Music-artifacts/

# or cloud bucket (Backblaze B2 / S3 / Google Drive)
rclone sync VoiceModels/ remote:music-artifacts/VoiceModels/
```

## Voice model sources

Record the download URL for each model here so it can be re-fetched:

- (add entries as you download, e.g. `EdSheeranV3.zip — https://...`)
