"""``plcexport``: export one project into the common format, or validate an export folder."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True, help="PLC project export into the common format")


@app.command("one")
def export_one(
    project_dir: Path = typer.Argument(
        ..., exists=True, help="Project folder, or a single-file source such as a TIA archive"
    ),
    out: Path = typer.Option(..., "--out", help="Export folder to write"),
    extractor: str | None = typer.Option(None, "--extractor", help="Extractor id"),
) -> None:
    """Export one project (a folder, or a file such as ``.zap21``) into the common format."""
    from plcexport.one import export_project

    result = export_project(project_dir, out, extractor_id=extractor)
    typer.echo(f"{result.status}: {out}" + (f" ({result.reason})" if result.reason else ""))
    for v in result.violations:
        typer.echo(f"  - {v}", err=True)
    if result.status not in ("exported", "partial"):
        raise typer.Exit(code=1)


@app.command("validate")
def export_validate(export_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Validate an export folder against the common format v1."""
    from plcexport.format.validate import validate_export

    violations = validate_export(export_dir)
    for v in violations:
        typer.echo(v, err=True)
    if violations:
        typer.echo(f"{len(violations)} violation(s)", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"valid: {export_dir}")
