"""
This module defines the `MultiStaticFiles` class, a subclass of Starlette's `StaticFiles`,
that enables serving static files from multiple directories simultaneously.

By default, Starlette's `StaticFiles` class supports a single directory or package for static assets.
This enhancement addresses the limitation by allowing a list of directories to be registered,
providing a simple mechanism for serving files from multiple sources.

References:
- Related discussion: https://github.com/encode/starlette/issues/537

Classes:
- MultiStaticFiles: Extends `StaticFiles` to support multiple static folders via the `directories` parameter.
"""

import typing
from starlette.staticfiles import PathLike, StaticFiles


class MultiStaticFiles(StaticFiles):
    """
    A subclass of Starlette's StaticFiles that allows serving static files from multiple directories.
    """

    def __init__(self, directories: typing.List[PathLike] = [], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_directories = self.all_directories + directories
