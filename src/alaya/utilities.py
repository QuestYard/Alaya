def dict_to_namespace(data):
    """
    Recursively converts a dictionary (and nested dicts/lists of dicts)
    into a types.SimpleNamespace object.
    """
    from types import SimpleNamespace

    if isinstance(data, dict):
        # Convert dictionary items recursively
        return SimpleNamespace(
            **{key: dict_to_namespace(value) for key, value in data.items()}
        )

    elif isinstance(data, list):
        # Convert list items if they are dictionaries
        return [dict_to_namespace(item) for item in data]

    else:
        # Return all other types (strings, integers, etc.) unchanged
        return data


def generate_id() -> str:
    from uuid6 import uuid7

    return str(uuid7())
