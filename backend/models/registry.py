import importlib
import pkgutil

import models


def load_all_models() -> None:
    for module in pkgutil.iter_modules(models.__path__):
        if module.name != "registry":
            importlib.import_module(f"models.{module.name}")
