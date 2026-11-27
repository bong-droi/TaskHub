"""Kiểm tra Swagger/ReDoc, Bearer auth scheme và tài liệu error responses trong OpenAPI."""


async def test_swagger_and_redoc_are_served(anon) -> None:
    docs = await anon.get("/docs")
    redoc = await anon.get("/redoc")
    openapi = await anon.get("/openapi.json")
    assert docs.status_code == 200 and "SwaggerUIBundle" in docs.text
    assert redoc.status_code == 200 and "redoc" in redoc.text.lower()
    assert openapi.status_code == 200


async def test_openapi_documents_bearer_scheme_and_error_responses(anon) -> None:
    schema = (await anon.get("/openapi.json")).json()

    # 1. Bearer auth scheme (OAuth2PasswordBearer) + ErrorResponse schemas
    components = schema["components"]
    assert "OAuth2PasswordBearer" in components["securitySchemes"]
    assert {"ErrorResponse", "InternalErrorResponse"}.issubset(components["schemas"].keys())

    paths = schema["paths"]

    # 2. Public route: health chỉ có 200 + 500
    health_resps = paths["/api/v1/health"]["get"]["responses"]
    assert {"200", "500"}.issubset(health_resps.keys())
    assert "401" not in health_resps

    # 3. Auth routes
    assert "409" in paths["/api/v1/auth/register"]["post"]["responses"]
    assert {"401", "403"}.issubset(paths["/api/v1/auth/login"]["post"]["responses"].keys())

    # 4. Protected routes kế thừa 401 + 500, đồng thời khai báo lỗi nghiệp vụ riêng
    assert {"400", "401", "500"}.issubset(
        paths["/api/v1/users/me/password"]["post"]["responses"].keys()
    )
    assert {"400", "401", "403", "404", "409", "500"}.issubset(
        paths["/api/v1/projects/{project_id}/tasks"]["post"]["responses"].keys()
    )
    assert {"401", "403", "404", "500"}.issubset(
        paths["/api/v1/comments/{comment_id}"]["delete"]["responses"].keys()
    )
