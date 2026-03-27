"""Settings command — view and modify hamlet configuration."""
from __future__ import annotations

import dataclasses
import sys
from argparse import Namespace
from typing import Any


def _get_valid_keys() -> list[str]:
    """Return list of valid top-level setting keys."""
    from hamlet.config.settings import Settings
    return [f.name for f in dataclasses.fields(Settings)]


def _get_effective_terrain(settings) -> dict[str, Any]:
    """Return terrain dict merged with TerrainConfig defaults.

    The stored terrain dict may be sparse (only overrides). This merges it
    with the full TerrainConfig defaults so all sub-keys are accessible.
    """
    from hamlet.world_state.terrain import TerrainConfig
    tc = TerrainConfig()
    defaults = {f.name: getattr(tc, f.name) for f in dataclasses.fields(tc)}
    return {**defaults, **settings.terrain}


def _coerce_value(existing_value: Any, new_str: str) -> Any:
    """Parse new_str to the appropriate type based on the existing value's type."""
    # Handle null/none
    if new_str.lower() in ("null", "none"):
        return None
    # Handle bool strings
    if new_str.lower() == "true":
        return True
    if new_str.lower() == "false":
        return False
    # Match existing type
    if existing_value is not None:
        if isinstance(existing_value, bool):
            # bool check must come before int since bool is subclass of int
            raise ValueError(f"Expected 'true' or 'false' for boolean field, got: {new_str!r}")
        if isinstance(existing_value, int):
            try:
                return int(new_str)
            except ValueError:
                raise ValueError(f"Expected integer, got: {new_str!r}")
        if isinstance(existing_value, float):
            try:
                return float(new_str)
            except ValueError:
                raise ValueError(f"Expected float, got: {new_str!r}")
    # Default: keep as string
    return new_str


def settings_list() -> int:
    """Print all current settings as key=value pairs."""
    from hamlet.config.settings import Settings
    try:
        settings = Settings.load()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    for f in dataclasses.fields(settings):
        value = getattr(settings, f.name)
        if f.name == "terrain":
            terrain = _get_effective_terrain(settings)
            for sub_key, sub_val in sorted(terrain.items()):
                print(f"terrain.{sub_key} = {sub_val}")
        else:
            print(f"{f.name} = {value}")
    return 0


def settings_get(key: str) -> int:
    """Print the value for a single key. Supports dot notation for terrain sub-keys."""
    from hamlet.config.settings import Settings
    try:
        settings = Settings.load()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    valid_keys = _get_valid_keys()

    if "." in key:
        parts = key.split(".", 1)
        top_key, sub_key = parts[0], parts[1]
        if top_key != "terrain":
            print(f"Error: unknown key {key!r}. Valid keys: {', '.join(valid_keys)}", file=sys.stderr)
            return 1
        terrain = _get_effective_terrain(settings)
        if sub_key not in terrain:
            terrain_keys = [f"terrain.{k}" for k in sorted(terrain.keys())]
            print(
                f"Error: unknown terrain key {key!r}. Valid terrain keys: {', '.join(terrain_keys)}",
                file=sys.stderr,
            )
            return 1
        print(terrain[sub_key])
        return 0

    if key not in valid_keys:
        print(f"Error: unknown key {key!r}. Valid keys: {', '.join(valid_keys)}", file=sys.stderr)
        return 1

    value = getattr(settings, key)
    if key == "terrain":
        terrain = _get_effective_terrain(settings)
        for sub_key, sub_val in sorted(terrain.items()):
            print(f"terrain.{sub_key} = {sub_val}")
    else:
        print(value)
    return 0


def settings_set(key: str, value_str: str) -> int:
    """Update a setting in the config file."""
    from hamlet.config.settings import Settings
    try:
        settings = Settings.load()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    valid_keys = _get_valid_keys()

    if "." in key:
        parts = key.split(".", 1)
        top_key, sub_key = parts[0], parts[1]
        if top_key != "terrain":
            print(f"Error: unknown key {key!r}. Valid keys: {', '.join(valid_keys)}", file=sys.stderr)
            return 1
        terrain = _get_effective_terrain(settings)
        if sub_key not in terrain:
            terrain_keys = [f"terrain.{k}" for k in sorted(terrain.keys())]
            print(
                f"Error: unknown terrain key {key!r}. Valid terrain keys: {', '.join(terrain_keys)}",
                file=sys.stderr,
            )
            return 1
        old_value = terrain[sub_key]
        # Use TerrainConfig type hints for coercion when existing value is None
        from hamlet.world_state.terrain import TerrainConfig
        import typing
        tc_hints = typing.get_type_hints(TerrainConfig)
        hint = tc_hints.get(sub_key)
        coerce_from = old_value
        if coerce_from is None and hint is not None:
            # Extract base type from Optional[X] / X | None
            origin = getattr(hint, "__origin__", None)
            args = getattr(hint, "__args__", ())
            if origin is typing.Union or str(hint).startswith("typing.Union"):
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    coerce_from = non_none[0]()  # e.g. int() -> 0, float() -> 0.0
        try:
            new_value = _coerce_value(coerce_from, value_str)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        # Only store the override (sparse dict), merged on read
        updated_terrain = {**settings.terrain, sub_key: new_value}
        # Validate terrain by constructing TerrainConfig
        from hamlet.world_state.terrain import TerrainConfig
        effective = _get_effective_terrain(settings)
        effective[sub_key] = new_value
        tc_fields = {f.name for f in dataclasses.fields(TerrainConfig)}
        try:
            TerrainConfig(**{k: v for k, v in effective.items() if k in tc_fields})
        except (TypeError, ValueError) as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return 1
        settings.terrain = updated_terrain
        try:
            settings._validate()
        except ValueError as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return 1
        settings.save()
        print(f"{key}: {old_value} -> {new_value}")
        return 0

    if key not in valid_keys:
        print(f"Error: unknown key {key!r}. Valid keys: {', '.join(valid_keys)}", file=sys.stderr)
        return 1

    old_value = getattr(settings, key)
    if key == "terrain":
        print("Error: use dot notation to set terrain sub-keys, e.g. terrain.seed", file=sys.stderr)
        return 1

    try:
        new_value = _coerce_value(old_value, value_str)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    setattr(settings, key, new_value)

    try:
        settings._validate()
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 1

    settings.save()
    print(f"{key}: {old_value} -> {new_value}")
    return 0


def settings_command(args: Namespace) -> int:
    """Dispatch settings sub-commands."""
    sub = getattr(args, "settings_subcommand", None)
    if sub is None:
        return settings_list()
    if sub == "get":
        return settings_get(args.key)
    if sub == "set":
        return settings_set(args.key, args.value)
    print(f"Error: unknown settings subcommand {sub!r}", file=sys.stderr)
    return 1
