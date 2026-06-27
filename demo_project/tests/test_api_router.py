import pytest
from tengod.正官_法度调度.api_router import APIRouter, route, get, post, _default_router


class TestAPIRouterInit:
    def test_init_without_prefix(self):
        router = APIRouter()
        assert router.prefix == ""
        assert router._routes == {}
        assert router._middleware == []

    def test_init_with_prefix(self):
        router = APIRouter(prefix="/api")
        assert router.prefix == "/api"
        assert router._routes == {}
        assert router._middleware == []


class TestRouteDecorator:
    def test_route_decorator_registers_handler(self):
        router = APIRouter()

        @router.route("/hello")
        def hello():
            return "world"

        assert "/hello" in router._routes
        assert "GET" in router._routes["/hello"]
        # The stored handler is the original func, not the decorated wrapper
        assert router._routes["/hello"]["GET"]() == "world"

    def test_route_decorator_with_prefix(self):
        router = APIRouter(prefix="/api")

        @router.route("/hello")
        def hello():
            return "world"

        assert "/api/hello" in router._routes
        assert "GET" in router._routes["/api/hello"]

    def test_route_decorator_custom_method(self):
        router = APIRouter()

        @router.route("/submit", method="POST")
        def submit():
            return "ok"

        assert "/submit" in router._routes
        assert "POST" in router._routes["/submit"]

    def test_route_decorator_wraps_with_middleware(self):
        router = APIRouter()
        middleware_calls = []

        def mw(*args, **kwargs):
            middleware_calls.append(1)

        router.add_middleware(mw)

        @router.route("/test")
        def test_func():
            return "result"

        # The wrapper function returned by the decorator should call middleware
        test_func()
        assert middleware_calls == [1]

    def test_route_decorator_returns_callable(self):
        router = APIRouter()

        @router.route("/test")
        def test_func():
            return "ok"

        # The decorated function should still be callable
        result = test_func()
        assert result == "ok"


class TestShortcutDecorators:
    def test_get_shortcut(self):
        router = APIRouter()

        @router.get("/items")
        def list_items():
            return []

        assert "GET" in router._routes["/items"]

    def test_post_shortcut(self):
        router = APIRouter()

        @router.post("/items")
        def create_item():
            return "created"

        assert "POST" in router._routes["/items"]

    def test_put_shortcut(self):
        router = APIRouter()

        @router.put("/items/1")
        def update_item():
            return "updated"

        assert "PUT" in router._routes["/items/1"]

    def test_delete_shortcut(self):
        router = APIRouter()

        @router.delete("/items/1")
        def delete_item():
            return "deleted"

        assert "DELETE" in router._routes["/items/1"]


class TestAddMiddleware:
    def test_add_middleware_adds_to_list(self):
        router = APIRouter()

        def mw1():
            pass

        router.add_middleware(mw1)
        assert router._middleware == [mw1]

    def test_multiple_middleware_order(self):
        router = APIRouter()
        order = []

        def mw1(*args, **kwargs):
            order.append(1)

        def mw2(*args, **kwargs):
            order.append(2)

        router.add_middleware(mw1)
        router.add_middleware(mw2)

        @router.route("/test")
        def handler():
            return "ok"

        handler()
        assert order == [1, 2]

    def test_middleware_execution_in_decorator_wrapper(self):
        router = APIRouter()
        executed = []

        def mw(*args, **kwargs):
            executed.append("mw")

        router.add_middleware(mw)

        @router.route("/test")
        def handler():
            executed.append("handler")
            return "done"

        result = handler()
        assert result == "done"
        assert executed == ["mw", "handler"]


class TestDispatch:
    def test_dispatch_valid_path_and_method(self):
        router = APIRouter()

        @router.get("/hello")
        def hello():
            return "world"

        result = router.dispatch("/hello", "GET")
        assert result == "world"

    def test_dispatch_with_args(self):
        router = APIRouter()

        @router.get("/greet")
        def greet(name):
            return f"Hello, {name}"

        result = router.dispatch("/greet", "GET", "Alice")
        assert result == "Hello, Alice"

    def test_dispatch_with_kwargs(self):
        router = APIRouter()

        @router.get("/greet")
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}"

        result = router.dispatch("/greet", "GET", name="Bob", greeting="Hi")
        assert result == "Hi, Bob"

    def test_dispatch_with_args_and_kwargs(self):
        router = APIRouter()

        @router.post("/calc")
        def calc(a, b, op="add"):
            if op == "add":
                return a + b
            return a - b

        result = router.dispatch("/calc", "POST", 3, 4, op="sub")
        assert result == -1

    def test_dispatch_invalid_path_raises_value_error(self):
        router = APIRouter()

        @router.get("/exists")
        def exists():
            return "ok"

        with pytest.raises(ValueError, match="Route not found"):
            router.dispatch("/nonexistent", "GET")

    def test_dispatch_invalid_method_raises_value_error(self):
        router = APIRouter()

        @router.get("/item")
        def get_item():
            return "item"

        with pytest.raises(ValueError, match="Route not found"):
            router.dispatch("/item", "POST")

    def test_dispatch_with_prefix(self):
        router = APIRouter(prefix="/api")

        @router.get("/users")
        def users():
            return ["alice"]

        result = router.dispatch("/users", "GET")
        assert result == ["alice"]

        with pytest.raises(ValueError):
            router.dispatch("/api/users", "GET")


class TestListRoutes:
    def test_list_routes_empty(self):
        router = APIRouter()
        assert router.list_routes() == []

    def test_list_routes_single(self):
        router = APIRouter()

        @router.get("/test")
        def test():
            pass

        routes = router.list_routes()
        assert routes == [{"method": "GET", "path": "/test"}]

    def test_list_routes_multiple_methods_same_path(self):
        router = APIRouter()

        @router.get("/items")
        def get_items():
            pass

        @router.post("/items")
        def create_item():
            pass

        routes = router.list_routes()
        assert {"method": "GET", "path": "/items"} in routes
        assert {"method": "POST", "path": "/items"} in routes
        assert len(routes) == 2

    def test_list_routes_multiple_paths(self):
        router = APIRouter()

        @router.get("/a")
        def a():
            pass

        @router.post("/b")
        def b():
            pass

        routes = router.list_routes()
        assert len(routes) == 2
        assert {"method": "GET", "path": "/a"} in routes
        assert {"method": "POST", "path": "/b"} in routes


class TestModuleLevelFunctions:
    def test_module_route_function(self):
        # Reset the _default_router by creating a new one
        # We can't replace _default_router, but we can test the module-level
        # functions use it by checking they register on _default_router
        initial_count = len(_default_router.list_routes())

        @route("/module_test")
        def module_test():
            return "module"

        routes = _default_router.list_routes()
        assert {"method": "GET", "path": "/module_test"} in routes

    def test_module_get_function(self):
        @get("/module_get")
        def module_get():
            return "get"

        routes = _default_router.list_routes()
        assert {"method": "GET", "path": "/module_get"} in routes

    def test_module_post_function(self):
        @post("/module_post")
        def module_post():
            return "post"

        routes = _default_router.list_routes()
        assert {"method": "POST", "path": "/module_post"} in routes


class TestEdgeCases:
    def test_empty_path(self):
        router = APIRouter()

        @router.get("")
        def root():
            return "root"

        assert "" in router._routes
        result = router.dispatch("", "GET")
        assert result == "root"

    def test_empty_path_with_prefix(self):
        router = APIRouter(prefix="/api")

        @router.get("")
        def api_root():
            return "api"

        result = router.dispatch("", "GET")
        assert result == "api"

    def test_multiple_routes_same_path_different_methods(self):
        router = APIRouter()

        @router.get("/multi")
        def get_multi():
            return "GET"

        @router.post("/multi")
        def post_multi():
            return "POST"

        assert router.dispatch("/multi", "GET") == "GET"
        assert router.dispatch("/multi", "POST") == "POST"

    def test_multiple_middleware_execution_order(self):
        router = APIRouter()
        order = []

        def mw1(*args, **kwargs):
            order.append("mw1")

        def mw2(*args, **kwargs):
            order.append("mw2")

        def mw3(*args, **kwargs):
            order.append("mw3")

        router.add_middleware(mw1)
        router.add_middleware(mw2)
        router.add_middleware(mw3)

        @router.get("/order")
        def ordered():
            order.append("handler")
            return "ok"

        ordered()
        assert order == ["mw1", "mw2", "mw3", "handler"]

    def test_method_case_normalization(self):
        router = APIRouter()

        @router.route("/test", method="get")
        def test():
            return "ok"

        # Should be stored as uppercase
        assert "GET" in router._routes["/test"]
        assert "get" not in router._routes["/test"]