import os
from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import walk_packages


def recursive_import(path_str, host_module_name):
    """
    Recursively import all submodules of a package and hoist all classes found
    within them to the top-level namespace of the current module.

    This utility walks the package tree rooted at `path_str`, imports every
    (sub)module under `host_module_name`, inspects their attributes, and for
    each attribute that is a class, adds that class to the current module's
    global namespace (i.e., `globals()`), making it available as a direct
    top-level symbol.

    Primarily used to allow alembic to see all tables created within this folder.

    Parameters
    ----------
    path_str : str
        Filesystem path to the package directory that should be walked. This is
        typically the `__path__[0]` (or an element of `__path__`) of the package
        invoking this function.
    host_module_name : str
        The fully-qualified module name of the package being walked (e.g.,
        `"my_package"`). Submodules will be imported as
        `f"{host_module_name}.{module_name}"`.

    Returns
    -------
    None

    """
    for (module_finder, module_name, ispkg) in walk_packages([path_str]):

        if ispkg:
            recursive_import(os.path.join(module_finder.path, module_name), f"{host_module_name}.{module_name}")
        
        # import the module and iterate through its attributes
        module = import_module(f"{host_module_name}.{module_name}")
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)

            if isclass(attribute):            
                # Add the class to this package's variables
                globals()[attribute_name] = attribute


# iterate through the modules in the current package
package_dir = Path(__file__).resolve().parent

recursive_import(str(package_dir), __name__)