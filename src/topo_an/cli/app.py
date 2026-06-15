import sys
import traceback
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel

from topo_an.cli import analysis, validation

app = typer.Typer(no_args_is_help=True)


class WcamsTopos(BaseModel):
    dir: Path
    epsg: int
    ref: Path


class SporadicTopos(BaseModel):
    date: list[str]
    name: list[str]
    files: list[Path]
    ref: Path
    t_ref: str
    epsg: int
    roi: Path

class FilePair(BaseModel):
    wavecams: Path
    sporadic: Path
    t_sporadic: str

class Validation(BaseModel):
    pairs: list[FilePair]
    roi_val: Path
    outdir: Path

class AppConfig(BaseModel):
    wavecams_topos: WcamsTopos
    sporadic_topos: SporadicTopos
    outdir: Path
    validation: Validation


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)  # validation automatique


@app.command()
def main(
    input_yaml: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=True,
            help="Input yaml file containing parameters",
        ),
    ],
):
    # load configuration file
    conf = load_config(input_yaml)

    if not conf.wavecams_topos.dir.exists():
        raise typer.Exit("Wavecams topo directory does not exist")

    if not conf.outdir.exists():
        conf.outdir.mkdir(parents=True, exist_ok=True)

    try:
        # Run topo analysis
        analysis.main(conf)
        # Run topo validation
        validation.main(conf)


    except Exception as e:  # noqa: BLE001
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    app()
