import worlds.LauncherComponents as LauncherComponents


def launch_app() -> None:
    from .app import main
    LauncherComponents.launch(main, name="GenerateUntilSuccessful")


LauncherComponents.components.append(
    LauncherComponents.Component(
        "Generate Until Successful",
        func=launch_app,
        component_type=LauncherComponents.Type.TOOL,
        description="Keep attempting to generate a multiworld with the YAMLs in the players folder until successful.",
    )
)

