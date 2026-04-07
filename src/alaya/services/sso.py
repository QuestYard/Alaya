from .. import conf


class SSOUnavailableError(Exception):
    pass


class AccountNotExistsError(Exception):
    pass


class PasswordIncorrectError(Exception):
    pass


async def sso_authenticate(account: str, password: str | None) -> dict:
    """
    Authenticate user by account and password, or only by account for stored users.
    """
    if conf.app.sso is not None:
        # Call real SSO API later
        raise SSOUnavailableError()

    return native_sso_authenticate(account, password)


async def sso_change_password(
    account: str, old_password: str, new_password: str
) -> None:
    if conf.app.sso is not None:
        # Call real SSO API later
        raise SSOUnavailableError()

    native_sso_change_password(account, old_password, new_password)


# --- Native Mock SSO for developing and testing ---


def native_sso_authenticate(account: str, password: str | None) -> dict[str, str]:
    import csv
    from pathlib import Path

    with open(Path.cwd() / "native_sso.csv", "r", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            if row["account"] == account:
                if password is None or row["password"] == password.strip():
                    sso_info = row.copy()
                    sso_info.pop("password")
                    return sso_info
                raise PasswordIncorrectError(f"User '{account}' password incorrect.")
        raise AccountNotExistsError(f"User '{account}' not exists.")


def native_sso_change_password(
    account: str, old_password: str, new_password: str
) -> None:
    import csv
    from pathlib import Path

    with open(Path.cwd() / "native_sso.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = {row["account"]: row for row in reader}
    if account not in rows:
        raise AccountNotExistsError(f"User '{account}' not exists.")
    if rows[account]["password"] != old_password.strip():
        raise PasswordIncorrectError(f"User '{account}' old password incorrect.")
    rows[account]["password"] = new_password.strip()
    with open(Path.cwd() / "native_sso.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[account].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows.values())
