# PitchCraft frontend

This is a static HTML/CSS/JavaScript client. It can be hosted on GitHub Pages and communicates with the processing backend through HTTPS.

Open `index.html` through a local static server to use the demo experience. With `API_BASE_URL` left blank in `app.js`, selecting any supported audio file produces sample notes without uploading the file.

When the backend is available, set `CONFIG.API_BASE_URL` near the top of `app.js` to its HTTPS origin:

```js
API_BASE_URL: "https://api.example.com",
```

The API must allow cross-origin requests from the website's exact origin. Do not use `*` once authentication or cookies are introduced.

## Expected API

### Start a job

`POST /api/jobs` using `multipart/form-data` with the audio file in the `audio` field.

```json
{ "id": "job_abc123", "status": "queued" }
```

### Check a job

`GET /api/jobs/{id}`

While processing:

```json
{
  "id": "job_abc123",
  "status": "processing",
  "stage": "detect",
  "progress": 67,
  "message": "Listening for pitch…"
}
```

Valid stages are `upload`, `separate`, `detect`, and `transcribe`.

When complete:

```json
{
  "id": "job_abc123",
  "status": "complete",
  "progress": 100,
  "result": {
    "duration": 12.4,
    "midi_url": "/api/jobs/job_abc123/files/melody.mid",
    "musicxml_url": "/api/jobs/job_abc123/files/melody.musicxml",
    "notes": [
      { "start_time": 0, "duration": 0.5, "midi_note": 60, "velocity": 82 }
    ]
  }
}
```

When failed:

```json
{ "id": "job_abc123", "status": "failed", "error": "No vocal melody was detected." }
```

The browser uses the lightweight `notes` array for its built-in audio preview. It does not need to parse the MIDI file. Generated files can be temporary signed URLs, but they should remain valid long enough for the user to download them.

## Production checklist

- Serve both the website and API over HTTPS.
- Restrict CORS to the production website origin.
- Validate file type, size, and decoded audio duration on the server.
- Generate unpredictable job IDs and never expose server file paths.
- Limit submissions per IP or account.
- Queue processing rather than running Demucs inside the upload request.
- Delete uploads and results automatically after a documented period.
- Add authentication only if the beta needs private access or saved history.
