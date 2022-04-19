from typer import Exit, Option, Typer, Argument, echo
from typing import Optional

from pyaerocom import const, tools, __version__, __package__

main = Typer()


def _confirm():
    """
    Ask user to confirm something

    Returns
    -------
    bool
        True if user answers yes, else False
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("[Y/N]? ").lower()
    return answer == "y"


def version_callback(value: bool):  # pragma: no cover
    if not value:
        return

    echo(f"{__package__} {__version__}")
    raise Exit()


@main.callback()
def callback(version: Optional[bool] = Option(None, "--version", "-V", callback=version_callback)):
    """Pyaerocom Command Line Interface"""


@main.command()
def browse(database: str = Argument(..., help="Provide database name.")):
    """Browse database e.g., browse <DATABASE>"""
    print(f"Searching database for matches of {database}")
    print(tools.browse_database(database))


@main.command()
def clearcache():
    """Delete cached data objects"""

    print("Are you sure you want to delete all cached data objects?")
    if _confirm():
        print("OK then.... here we go!")
        tools.clear_cache()
    else:
        print("Wise decision, pyaerocom will handle it for you automatically anyways ;P")


@main.command()
def ppiaccess():
    """Check if MetNO PPI can be accessed"""
    print("True") if const.has_access_lustre else print("False")


if __name__ == "__main__":
    main()
