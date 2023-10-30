from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import json
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
import requests

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret")

config = Config(".env")
oauth = OAuth(config=config)

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/user.birthday.read https://www.googleapis.com/auth/user.gender.read"
    },
)


@app.get("/")
def home(request: Request):
    user = request.session.get("user")
    if user:
        data = json.dumps(user)
        html = (
            f"<pre>Hello, {user['name']}</pre>"
            f"<pre>Here is your data {data}</pre>"
            """<button
        class="btn success"
        style="margin-left: 550px; margin-top: 250px; font-size: 20px"
        >
        <a href="/logout">Logout</a>
        </button>"""
        )
        return HTMLResponse(html)
    return HTMLResponse(
        """<button
        class="btn success"
        style="margin-left: 550px; margin-top: 250px; font-size: 20px"
        >
        <a href="/login">Login with Google</a>
        </button>"""
    )


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth")
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTMLResponse(f"<h1>{error.error}</h1>")

    personal_data_token = (
        "https://people.googleapis.com/v1/people/me?personFields=genders,birthdays"
    )
    person_data = requests.get(
        personal_data_token,
        headers={"Authorization": f"Bearer {token['access_token']}"},
    ).json()
    token["person_data"] = person_data

    user = token.get("userinfo")
    user["person_data"] = token.get("person_data")

    if user:
        request.session["user"] = dict(user)
    return RedirectResponse(url="/")


@app.get("/logout")
def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")
