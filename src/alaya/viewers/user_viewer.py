from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..events import ClientEvents

from ..models import User
from ..services import (
    SSOUnavailableError,
    AccountNotExistsError,
    PasswordIncorrectError,
    sso_change_password,
    login,
)
from .. import logger, conf
from nicegui import ui


def user_manager(app, events: ClientEvents):
    current_user = User(**app.storage.user.get("current_user", {}))

    with ui.dialog() as dialog, ui.card().classes("p-8 w-xl max-w-full gap-2"):
        ui.label("用户登录").classes("text-h6 font-bold text-center w-full")
        ui.markdown(
            "请填写在 OA 系统登记的<u>**手机号**</u>以注册或登录。"
            "系统自动验证用户并获取姓名、组织机构等相关信息，无需用户填写。"
        ).classes("text-xs text-left text-zinc-500 w-full")
        account_inp = (
            ui.input(
                label="用户账号:",
                placeholder="OA 登记的手机号码",
                value=current_user.account if current_user.id else "",
            )
            .classes("w-full")
            .on(
                "keydown.enter",
                lambda e: submit(e),
                js_handler="""
            (e) => {
                if (!e.shiftKey && !e.isComposing) {
                    emit(e);
                    e.preventDefault();
                }
            }""",
            )
        )
        password_inp = (
            ui.input(label="用户密码:", password=True, value="")
            .classes("w-full")
            .on(
                "keydown.enter",
                lambda e: submit(e),
                js_handler="""
            (e) => {
                if (!e.shiftKey && !e.isComposing) {
                    emit(e);
                    e.preventDefault();
                }
            }""",
            )
        )
        with ui.row().classes("w-full gap-4 mt-8 justify-end"):
            submit_btn = (
                ui.button("登录", color="emerald-800")
                .props("flat")
                .classes("text-white px-6")
            )
            logout_btn = (
                ui.button("登出", color="zinc-200")
                .props("flat")
                .classes("text-gray-600 px-6")
            )
            change_password_btn = (
                ui.button("修改密码", color="zinc-200")
                .props("flat")
                .classes("text-gray-600 px-6")
            )

    # --- Callback functions ---
    async def submit(e):
        _ = e
        submitted_account = account_inp.value.strip()
        if not submitted_account or submitted_account.lower() == "guest":
            ui.notify("输入的用户账户无效。", type="warning")
            return
        submitted_password = password_inp.value.strip()
        try:
            user = await login(submitted_account, submitted_password)
            ui.notify(f"用户{user.username}({user.account})验证通过。", type="positive")
            app.storage.user["current_user"] = user.model_dump()
            events.user_logged_in.emit(user.account)
            logger.info(f"User {user.username}({user.account}) logged in.")
            dialog.close()
        except SSOUnavailableError:
            ui.notify("SSO 服务器不可用，无法验证用户身份。", type="negative")
        except AccountNotExistsError:
            ui.notify(f"账户（{submitted_account}）不存在。", type="negative")
        except PasswordIncorrectError:
            ui.notify(f"账户（{submitted_account}）密码错误。", type="negative")
        except Exception as e:
            ui.notify("未知原因登录失败", type="negative")

    def logout(e):
        _ = e
        app.storage.user["current_user"] = User().model_dump()
        events.user_logged_in.emit(app.storage.user["current_user"]["account"])
        dialog.close()

    async def change_password(e):
        _ = e
        if conf.webui_app.sso is not None:
            ui.notify("请在组织机构用户中心进行密码更改。", type="warning")
            return
        if not current_user.id:
            ui.notify("当前为访客身份，不能更改密码。", type="warning")
            return
        dialog.close()
        change_password_and_login(current_user, app, events)

    # --- Binding properties and callbacks ---
    logout_btn.on_click(logout)
    submit_btn.on_click(submit)
    change_password_btn.on_click(change_password)

    dialog.open()


def change_password_and_login(user: User, app, events: ClientEvents):
    with ui.dialog() as dialog, ui.card().classes("p-8 w-xl max-w-full gap-2"):
        ui.label(f"用户 {user.username}（{user.account}）更改密码").classes(
            "text-h6 font-bold text-center w-full"
        )
        old_password_inp = (
            ui.input(label="用户原密码:", password=True, value="")
            .classes("w-full")
            .on(
                "keydown.enter",
                lambda e: submit(e),
                js_handler="""
            (e) => {
                if (!e.shiftKey && !e.isComposing) {
                    emit(e);
                    e.preventDefault();
                }
            }""",
            )
        )
        new_password_inp = (
            ui.input(label="用户新密码:", password=True, value="")
            .classes("w-full")
            .on(
                "keydown.enter",
                lambda e: submit(e),
                js_handler="""
            (e) => {
                if (!e.shiftKey && !e.isComposing) {
                    emit(e);
                    e.preventDefault();
                }
            }""",
            )
        )
        ensure_password_inp = (
            ui.input(label="确认新密码:", password=True, value="")
            .classes("w-full")
            .on(
                "keydown.enter",
                lambda e: submit(e),
                js_handler="""
            (e) => {
                if (!e.shiftKey && !e.isComposing) {
                    emit(e);
                    e.preventDefault();
                }
            }""",
            )
        )
        with ui.row().classes("w-full gap-4 mt-8 justify-end"):
            submit_btn = (
                ui.button("确认并登录", color="emerald-800")
                .props("flat")
                .classes("text-white px-6")
            )

    # --- Callback functions ---
    async def submit(e):
        _ = e
        old_password = old_password_inp.value.strip()
        new_password = new_password_inp.value.strip()
        if new_password != ensure_password_inp.value.strip():
            ui.notify("新密码两次输入不一致，请重新输入。", type="negative")
            return
        if new_password == old_password:
            ui.notify("新旧密码相同，无需更改。", type="warning")
            return
        try:
            await sso_change_password(user.account, old_password, new_password)
            ui.notify(f"用户{user.username}({user.account})验证通过。", type="positive")
            app.storage.user["current_user"] = user.model_dump()
            events.user_logged_in.emit(user.account)
            logger.info(f"User {user.username}({user.account}) logged in.")
            dialog.close()
        except SSOUnavailableError:
            ui.notify("请在组织机构用户中心进行密码更改。", type="negative")
        except AccountNotExistsError:
            ui.notify(f"账户（{user.account}）不存在。", type="negative")
        except PasswordIncorrectError:
            ui.notify("原密码错误，请重试。", type="negative")
        except Exception as e:
            ui.notify("未知原因更改密码失败", type="negative")

    # --- Binding properties and callbacks ---
    submit_btn.on_click(submit)

    dialog.open()
