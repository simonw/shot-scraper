from typing import Annotated, Literal, Union

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    PositiveInt,
    ValidationError,
    field_validator,
    model_validator,
)


class StoryboardError(ValueError):
    pass


class StoryboardBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StoryboardViewport(StoryboardBaseModel):
    width: PositiveInt | None = None
    height: PositiveInt | None = None


class CursorOptions(StoryboardBaseModel):
    visible: bool = True
    clicks: bool = True
    color: str = "#ff4f00"
    size: PositiveInt = 18
    click_size: PositiveInt = 44


class ClickAction(StoryboardBaseModel):
    action: Literal["click"]
    selector: str
    button: Literal["left", "right", "middle"] | None = None
    count: PositiveInt | None = None


class TypeAction(StoryboardBaseModel):
    action: Literal["type"]
    into: str | None = None
    selector: str | None = None
    text: str
    delay_ms: NonNegativeFloat | None = None

    @model_validator(mode="after")
    def require_selector(self):
        if not self.into and not self.selector:
            raise ValueError("type: must define into: or selector:")
        return self

    @property
    def target_selector(self):
        return self.into or self.selector


class FillAction(StoryboardBaseModel):
    action: Literal["fill"]
    into: str | None = None
    selector: str | None = None
    text: str

    @model_validator(mode="after")
    def require_selector(self):
        if not self.into and not self.selector:
            raise ValueError("fill: must define into: or selector:")
        return self

    @property
    def target_selector(self):
        return self.into or self.selector


class PressAction(StoryboardBaseModel):
    action: Literal["press"]
    key: str
    selector: str | None = None


class ScrollAction(StoryboardBaseModel):
    action: Literal["scroll"]
    x: float = 0
    y: float = 0
    to: str | None = None
    duration: NonNegativeFloat = 0


class PauseAction(StoryboardBaseModel):
    action: Literal["pause"]
    seconds: NonNegativeFloat


class WaitForAction(StoryboardBaseModel):
    action: Literal["wait_for"]
    selector: str


class WaitForUrlAction(StoryboardBaseModel):
    action: Literal["wait_for_url"]
    url: str


class ExpectAction(StoryboardBaseModel):
    action: Literal["expect"]
    selector: str | None = None
    text: str | None = None
    timeout: PositiveInt | None = None

    @model_validator(mode="after")
    def require_target(self):
        if self.selector is None and self.text is None:
            raise ValueError("expect: needs a selector: and/or text:")
        return self


class ExpectGoneAction(StoryboardBaseModel):
    action: Literal["expect_gone"]
    selector: str | None = None
    text: str | None = None
    timeout: PositiveInt | None = None

    @model_validator(mode="after")
    def require_target(self):
        if self.selector is None and self.text is None:
            raise ValueError("expect_gone: needs a selector: and/or text:")
        return self


class OpenAction(StoryboardBaseModel):
    action: Literal["open"]
    url: str


class JavascriptAction(StoryboardBaseModel):
    action: Literal["javascript", "js"]
    code: str


class ScreenshotAction(StoryboardBaseModel):
    action: Literal["screenshot"]
    output: str
    selector: str | None = None
    full_page: bool = False


class ShAction(StoryboardBaseModel):
    action: Literal["sh"]
    command: str | list[str]


class PythonAction(StoryboardBaseModel):
    action: Literal["python"]
    code: str


StoryboardAction = Annotated[
    Union[
        ClickAction,
        TypeAction,
        FillAction,
        PressAction,
        ScrollAction,
        PauseAction,
        WaitForAction,
        WaitForUrlAction,
        ExpectAction,
        ExpectGoneAction,
        OpenAction,
        JavascriptAction,
        ScreenshotAction,
        ShAction,
        PythonAction,
    ],
    Field(discriminator="action"),
]

STORYBOARD_ACTIONS = {
    "click",
    "type",
    "fill",
    "press",
    "scroll",
    "pause",
    "wait_for",
    "wait_for_url",
    "expect",
    "expect_gone",
    "open",
    "javascript",
    "js",
    "screenshot",
    "sh",
    "python",
}


class StoryboardScene(StoryboardBaseModel):
    name: str | None = None
    open: str | None = None
    wait_for: str | None = None
    wait_for_url: str | None = None
    sh: str | list[str] | None = None
    python: str | None = None
    do: list[StoryboardAction] = Field(default_factory=list)

    @field_validator("do", mode="before")
    @classmethod
    def normalize_actions(cls, actions):
        if actions is None:
            return []
        if not isinstance(actions, list):
            raise ValueError("do: must be a list")
        return [_normalize_storyboard_action(action) for action in actions]


class Storyboard(StoryboardBaseModel):
    output: str | None = None
    url: str | None = None
    sh: str | list[str] | None = None
    python: str | None = None
    server: str | list[str | int] | None = None
    viewport: StoryboardViewport = Field(default_factory=StoryboardViewport)
    cursor: CursorOptions | None = None
    wait: NonNegativeFloat | None = None
    wait_for: str | None = None
    wait_for_url: str | None = None
    javascript: str | None = None
    scenes: list[StoryboardScene] = Field(default_factory=list)

    @field_validator("cursor", mode="before")
    @classmethod
    def normalize_cursor(cls, cursor):
        if cursor is True:
            return {}
        if cursor is False:
            return None
        return cursor

    @model_validator(mode="after")
    def validate_storyboard(self):
        if not self.scenes:
            raise ValueError("Storyboard must define a non-empty scenes: list")
        if not self.url and not self.scenes[0].open:
            raise ValueError("Storyboard must define url: or open: in the first scene")
        return self

    def viewport_size(self):
        width = self.viewport.width or 1280
        height = self.viewport.height or 720
        return {"width": width, "height": height}


def load_storyboard(storyboard_file):
    storyboard_config = yaml.safe_load(storyboard_file)
    if storyboard_config is None:
        raise StoryboardError("Storyboard YAML file cannot be empty")
    if not isinstance(storyboard_config, dict):
        raise StoryboardError("Storyboard YAML file must contain a mapping")
    try:
        return Storyboard.model_validate(storyboard_config)
    except ValidationError as ex:
        raise StoryboardError(_format_storyboard_validation_error(ex))


def _normalize_storyboard_action(action):
    if not isinstance(action, dict) or len(action) != 1:
        raise ValueError("actions must be single-key mappings")

    action_name, value = next(iter(action.items()))
    if action_name not in STORYBOARD_ACTIONS:
        raise ValueError(f"Unknown storyboard action: {action_name}")

    if action_name == "click":
        if isinstance(value, str):
            return {"action": "click", "selector": value}
        if isinstance(value, dict):
            return {"action": "click", **value}
        raise ValueError("click: must be a selector string or mapping")

    if action_name in ("type", "fill"):
        if isinstance(value, dict):
            return {"action": action_name, **value}
        raise ValueError(f"{action_name}: must be a mapping")

    if action_name == "press":
        if isinstance(value, str):
            return {"action": "press", "key": value}
        if isinstance(value, dict):
            return {"action": "press", **value}
        raise ValueError("press: must be a key string or mapping")

    if action_name == "scroll":
        if isinstance(value, (int, float)):
            return {"action": "scroll", "y": value}
        if isinstance(value, dict):
            return {"action": "scroll", **value}
        raise ValueError("scroll: must be a number or mapping")

    if action_name == "pause":
        return {"action": "pause", "seconds": value}

    if action_name == "wait_for":
        return {"action": "wait_for", "selector": value}

    if action_name == "wait_for_url":
        return {"action": "wait_for_url", "url": value}

    if action_name in ("expect", "expect_gone"):
        if isinstance(value, str):
            return {"action": action_name, "selector": value}
        if isinstance(value, dict):
            value = dict(value)
            # `contains:` reads naturally as an alias for the text substring
            if "contains" in value and "text" not in value:
                value["text"] = value.pop("contains")
            return {"action": action_name, **value}
        raise ValueError(f"{action_name}: must be a selector string or mapping")

    if action_name == "open":
        return {"action": "open", "url": value}

    if action_name in ("javascript", "js"):
        return {"action": action_name, "code": value}

    if action_name == "screenshot":
        if isinstance(value, str):
            return {"action": "screenshot", "output": value}
        if isinstance(value, dict):
            return {"action": "screenshot", **value}
        raise ValueError("screenshot: must be an output string or mapping")

    if action_name == "sh":
        if isinstance(value, (str, list)):
            return {"action": "sh", "command": value}
        raise ValueError("sh: must be a string or list")

    if action_name == "python":
        if isinstance(value, str):
            return {"action": "python", "code": value}
        raise ValueError("python: must be a string")


def _format_storyboard_validation_error(validation_error):
    errors = []
    for error in validation_error.errors():
        location = ".".join(str(bit) for bit in error["loc"])
        message = error["msg"]
        if message.startswith("Value error, "):
            message = message[len("Value error, ") :]
        if location:
            errors.append(f"{location}: {message}")
        else:
            errors.append(message)
    return "\n".join(errors)
