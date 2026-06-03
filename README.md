# lianton_login

A small local web helper for getting a carrier app login session value by SMS verification.

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5123
```

## Desktop Window

```bash
pip install -r requirements.txt pywebview
python desktop.py
```

The desktop entry opens the page inside its own local window.

## Docker

```bash
docker run -d \
  --name lianton_login \
  -p 5123:5123 \
  iguang9881/unicom_login:latest
```

Then open:

```text
http://127.0.0.1:5123
```

## Build Docker Image

```bash
docker build -t iguang9881/unicom_login:latest .
docker push iguang9881/unicom_login:latest
```

## Environment Variables

| Name | Default | Description |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Bind address for local Python runs. Docker sets this to `0.0.0.0`. |
| `PORT` | `5123` | Web server port. |
| `FLASK_DEBUG` | `0` | Set to `1` only for local debugging. |
| `FLASK_SECRET_KEY` | random on start | Optional stable Flask session key. |

## Notes

- Keep this service local or behind a private network.
- The generated session value is sensitive.
- Successful results are saved locally in `data/token_history.json`.
- Use the clear button in the web page to remove saved results.
