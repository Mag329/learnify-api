from datetime import date, datetime, timedelta, timezone
from json import JSONDecodeError
from typing import Optional, TypeVar, Union

import aiohttp
from pydantic import RootModel

from learnifyapi.types import Type, User, Book, GdzAnswer

from .exceptions import APIError

_type = TypeVar("_type")


class LearnifyAPI:
    def __init__(
        self, token: str, base_url: str = "https://learnify.mag329.tech/api/v1"
    ):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._default_headers = {"Authorization": f"Bearer {token}"}
        self.session: aiohttp.ClientSession | None = None

    def headers(
        self, require_token: bool = True, custom_headers: Optional[dict] = None
    ):
        if custom_headers:
            for key, value in custom_headers.copy().items():
                if value is None:
                    del custom_headers[key]
                elif not isinstance(value, str):
                    custom_headers[key] = str(value)

        HEADERS = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if not self.token and require_token:
            msg = "Token is required!"
            raise ValueError(msg)
        elif require_token:
            HEADERS.update({"Authorization": f"Bearer {self.token}"})

        HEADERS.update(custom_headers or {})
        return HEADERS

    @staticmethod
    def init_params(url: str, params: dict) -> str:
        boolean = {True: "true", False: "false"}
        return (
            (
                f"{url}?"
                + "&".join(
                    [
                        f"{X}={Y}"
                        for X, Y in {
                            X: (
                                Y
                                if isinstance(Y, (str, float, int))
                                else (
                                    boolean[Y]
                                    if isinstance(Y, bool)
                                    else "null" if Y is None else str(Y)
                                )
                            )
                            for X, Y in params.items()
                        }.items()
                    ]
                )
            )
            if params
            else url
        )

    @staticmethod
    def datetime_to_string(dt: Optional[Union[datetime, date]] = None) -> str:
        """Сконвертировать ``datetime.datetime`` объект в строку(``str``) для использования в URL (METHOD)\n~~~"""
        if not dt:
            dt = datetime.now(tz=timezone(timedelta(hours=3), "MSK"))
        return (
            f"{dt.year}-{dt.month:02}-{dt.day:02}T{dt.hour:02}:{dt.minute:02}:{dt.second:02}"
            if isinstance(dt, datetime)
            else f"{dt.year}-{dt.month:02}-{dt.day:02}"
        )

    @staticmethod
    def date_to_string(date: Optional[Union[datetime, date]] = None) -> str:
        """Сконвертировать ``datetime.date`` объект в строку(``str``) для использования в URL (METHOD)\n~~~"""
        if not date:
            date = datetime.now(tz=timezone(timedelta(hours=3), "MSK")).date()
        return f"{date.year}-{date.month:02}-{date.day:02}"

    @staticmethod
    def parse_list_models(model: _type, response: str) -> list[_type]:
        class ListModels(RootModel[list[model] | None]):
            root: list[model] | None = None

        return ListModels.model_validate_json(response).root

    @staticmethod
    async def _check_response(response: aiohttp.ClientResponse):
        if response.status >= 400:
            try:
                json_response = await response.json()

                if isinstance(json_response, dict):
                    raise APIError(
                        status_code=response.status,
                        message=json_response.get("description", str(json_response))
                    )
            except (JSONDecodeError, aiohttp.ContentTypeError) as error:
                raise APIError(
                    status_code=response.status,
                    message=json_response.get("description", str(json_response))
                ) from error

    async def request(
        self,
        method: str,
        path: str,
        custom_headers: Optional[dict] = None,
        model: Optional[type[Type]] = None,
        is_list: bool = False,
        return_json: bool = False,
        return_raw_text: bool = False,
        required_token: bool = True,
        return_raw_response: bool = False,
        **kwargs,
    ):
        if not self.session:
            raise RuntimeError(
                "Session not initialized. Use `async with AsyncAPIClient(...)` or call `await client.__aenter__()`."
            )

        params = kwargs.pop("params", {})

        # Используем self.session, а не создаём новый
        async with self.session.request(
            method=method,
            url=self.init_params(self.base_url + path, params),
            headers=self.headers(required_token, custom_headers),
            **kwargs,
        ) as response:
            await self._check_response(response)
            raw_text = await response.text()

            if not raw_text:
                return None

            return (
                response
                if return_raw_response
                else (
                    await response.json()
                    if return_json
                    else (
                        raw_text
                        if return_raw_text
                        else (
                            self.parse_list_models(model, raw_text)
                            if is_list
                            else (
                                model.model_validate_json(raw_text)
                                if model
                                else raw_text
                            )
                        )
                    )
                )
            )

    async def create_user(
        self,
        user_id: int,
        expires_at: Optional[date] = None,
        plan_type: Optional[str] = None,
    ) -> User:
        body: dict = {"user_id": user_id}

        if expires_at is not None:
            body["expires_at"] = expires_at.isoformat()

        if plan_type is not None:
            body["plan_type"] = plan_type

        return await self.request(
            method="POST",
            path=f"/premium/users",
            json=body,
            model=User,
        )
        
    async def get_user(self, user_id: int) -> User:
        return await self.request(
            method="GET",
            path=f"/premium/users/{user_id}",
            model=User,
        )

    async def update_user(
        self,
        user_id: int,
        expires_at: Optional[date] = None,
        plan_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        body: dict = {}

        if expires_at is not None:
            body["expires_at"] = expires_at.isoformat()
        if plan_type is not None:
            body["plan_type"] = plan_type
        if is_active is not None:
            body["is_active"] = is_active

        if not body:
            raise ValueError("No fields provided for update")

        return await self.request(
            method="PUT",
            path=f"/premium/users/{user_id}",
            json=body,
            model=User,
        )
        
    async def delete_user(self, user_id: int) -> None:
        await self.request(
            method="DELETE",
            path=f"/premium/users/{user_id}",
        )
        
    async def activate_subscription(self, user_id: int, plan: str) -> User:
        return await self.request(
            method="POST",
            path=f"/premium/users/{user_id}/subscribe",
            model=User,
            json={
                "plan": plan,
            }
        )
        
    async def deactivate_subscription(self, user_id: int) -> User:
        return await self.request(
            method="POST",
            path=f"/premium/users/{user_id}/unsubscribe",
            model=User
        )
        
    async def check_subscription(self, user_id: int) -> bool:
        return await self.request(
            method="GET",
            path=f"/premium/users/{user_id}/subscription",
            return_raw_text=True
        )


    async def create_book(
        self,
        user_id: int,
        url: str,
        subject_id: Optional[int] = None,
        subject_name: Optional[str] = None,
        search_by: Optional[str] = None
    ) -> Book:
        body: dict = {
            "user_id": user_id,
            "url": url
        }

        if subject_id is not None:
            body["subject_id"] = subject_id

        if subject_name is not None:
            body["subject_name"] = subject_name
        
        if search_by is not None:
            body["search_by"] = search_by

        return await self.request(
            method="POST",
            path=f"/premium/gdz/books",
            json=body,
            model=Book,
        )
        
    async def get_book_by_id(self, book_id: int) -> Book:
        return await self.request(
            method="GET",
            path=f"/premium/gdz/book/{book_id}",
            model=Book,
        )
        
    async def get_book(
        self,
        user_id: str,
        book_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        subject_name: Optional[str] = None,
    ) -> Book:
        params: dict = {"user_id": user_id}
        
        if book_id is not None:
            params["book_id"] = book_id
        if subject_id is not None:
            params["subject_id"] = subject_id
        if subject_name is not None:
            params["subject_name"] = subject_name

        return await self.request(
            method="GET",
            path="/premium/gdz/books/search",
            params=params,
            model=Book,
        )

    async def update_book(
        self,
        user_id: int,
        book_id: int,
        url: Optional[str] = None,
        subject_id: Optional[int] = None,
        subject_name: Optional[str] = None,
        search_by: Optional[str] = None
    ) -> Book:
        body: dict = {}

        if url is not None:
            body["url"] = url
        if subject_id is not None:
            body["subject_id"] = subject_id
        if subject_name is not None:
            body["subject_name"] = subject_name
        if search_by is not None:
            body["search_by"] = search_by

        if not body:
            raise ValueError("No fields provided for update")

        return await self.request(
            method="PUT",
            path=f"/premium/gdz/books/{book_id}",
            json=body,
            model=Book,
            params={"user_id": user_id},
        )
        
    async def delete_book(self, user_id: int, book_id: int) -> None:
        await self.request(
            method="DELETE",
            path=f"/premium/gdz/books/{book_id}",
            params={"user_id": user_id},
        )
        
        
    async def get_gdz_answers(
        self,
        task_text: str,
        user_id: Optional[int] = None,
        book_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        subject_name: Optional[str] = None,
        book_url: Optional[str] = None,
        search_by: Optional[str] = None
    ):
        params = {"task_text": task_text}

        if user_id is not None:
            params["user_id"] = user_id
        if book_id is not None:
            params["book_id"] = book_id
        if subject_id is not None:
            params["subject_id"] = subject_id
        if subject_name is not None:
            params["subject_name"] = subject_name
        if book_url is not None:
            params["book_url"] = book_url
        if search_by is not None:
            params["search_by"] = search_by

        return await self.request(
            method="GET",
            path="/premium/gdz/books/gdz",
            params=params,
            model=GdzAnswer,
        )


    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            self.session = None
