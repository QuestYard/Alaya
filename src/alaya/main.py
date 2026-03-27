# --- App Entry Point ---
def start():
    print(
        "The Alaya-vijbana is constantly flowing and will eventually transform "
        "into wisdom."
    )
#     try:
#         ui.run(
#             root=root,
#             title="HuRAG WebUI - A ChatBot",
#             host=conf.webui_app.host,
#             port=conf.webui_app.port,
#             reload=__name__ in {"__main__", "__mp_main__"},
#             uvicorn_reload_dirs=src_dir,
#             favicon=asset("favicon.ico"),
#             storage_secret=storage_secret,
#         )
#     except KeyboardInterrupt:
#         pass


if __name__ in {"__main__", "__mp_main__"}:
    start()

