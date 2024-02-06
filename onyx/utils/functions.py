import difflib


def get_suggestions(
    unknown: str,
    options: list[str],
    n=3,
    cutoff=0.4,
    message_prefix: str | None = None,
) -> str:
    """
    Performs a case-insensitive comparison of an `unknown` against a list of `options`.

    Returns a message containing the suggestions.
    """

    options_map = {option.lower().strip(): option for option in options}

    close_matches = difflib.get_close_matches(
        word=unknown.lower().strip(),
        possibilities=options_map.keys(),
        n=n,
        cutoff=cutoff,
    )

    suggestions = [options_map[close_match] for close_match in close_matches]

    if message_prefix:
        message = message_prefix
    else:
        message = ""

    if suggestions:
        message += (
            f"{' ' if message else ''}Perhaps you meant: {', '.join(suggestions)}"
        )

    return message


def get_permission(
    app_label: str,
    action: str,
    code: str,
    field: str | None = None,
):
    """
    Returns a permission string for a given `app_label`, `action`, `code`, and `field`.

    The permission string is in the format:

    `<app_label>.<action>_<code>`

    If `field` is provided, the permission string will be in the format:

    `<app_label>.<action>_<code>__<field>`
    """

    if field:
        return f"{app_label}.{action}_{code}__{field}"
    else:
        return f"{app_label}.{action}_{code}"


def strtobool(val):
    """
    Convert a string representation of truth to True or False.

    True values are 'y', 'yes', 't', 'true', 'on', and '1'.

    False values are 'n', 'no', 'f', 'false', 'off', and '0'.

    Raises ValueError if 'val' is anything else.
    """

    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: {val}")
