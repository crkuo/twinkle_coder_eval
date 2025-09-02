"""
Enhanced Registry System
Based on mmengine design with dynamic loading and default_args support
"""

import inspect
import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union


class Registry:
    """
    Enhanced Registry
    Supports dynamic module loading and default_args
    """

    def __init__(
        self,
        name: str,
        build_func: Optional[Callable] = None,
        locations: List[str] = None,
    ):
        self._name = name
        self._module_dict: Dict[str, Type] = {}
        self._locations = locations or []
        self._imported = False
        self._build_func = build_func or self._default_build_func
        self.logger = logging.getLogger(__name__)

    def register_module(self, name: Optional[str] = None, force: bool = False):
        """
        Module registration decorator

        Args:
            name: Registration name, defaults to class name
            force: Whether to force overwrite existing registration
        """

        def _register(cls):
            module_name = name or cls.__name__

            if module_name in self._module_dict and not force:
                raise KeyError(f"'{module_name}' is already registered in {self._name}")

            self._module_dict[module_name] = cls
            return cls

        return _register

    def get(self, name: str, location: str = None) -> Optional[Type]:
        """
        Get registered module with dynamic loading support

        Args:
            name: Module name

        Returns:
            Registered class or None
        """
        # First try to get from already registered modules
        if name in self._module_dict:
            return self._module_dict[name]

        # If not found, try dynamic loading
        return self.get_module(name, location)

    def get_module(self, mod_name: str, location: str = None) -> Optional[Type]:
        """
        Get module with dynamic loading support for specified locations
        Suitable for loading new benchmarks or backends

        Args:
            name: Module name (e.g. "LeetCode")
            location: Module location template (e.g. "benchmark.{name}.{name}")

        Returns:
            Registered class or None

        Example:
            BENCHMARKS.get_module("LeetCode", "benchmark.{name}.{name}")
            # Will try to load benchmark.LeetCode.LeetCode module
        """
        # First try to get from already registered modules
        if mod_name in self._module_dict:
            return self._module_dict[mod_name]
        if location is None:
            location = f"{self._name}.{mod_name}.{mod_name}"
        # If location template is specified, format and load
        formatted_location = location.format(name=mod_name)
        try:
            importlib.import_module(formatted_location)
            self.logger.debug(f"Successfully imported {formatted_location}")

            # After loading, decorator will automatically register, try to get again
            if mod_name in self._module_dict:
                return self._module_dict[mod_name]
            else:
                return None
        except ImportError as e:
            self.logger.warning(f"Failed to import {formatted_location}: {e}")
            return None

    def _import_modules(self):
        """
        Dynamically load modules from specified locations
        """
        if self._imported:
            return

        for location in self._locations:
            try:
                importlib.import_module(location)
                self.logger.debug(f"Successfully imported {location}")
            except ImportError as e:
                self.logger.warning(f"Failed to import {location}: {e}")

        self._imported = True

    def build(self, cfg: Dict[str, Any]) -> Any:
        """
        Build object

        Args:
            cfg: Configuration dictionary containing 'type' field

        Returns:
            Built object instance
        """
        return self._build_func(cfg, self)

    def _default_build_func(self, cfg: Dict[str, Any], registry: "Registry") -> Any:
        """
        Default build function
        """
        cfg = cfg.copy()

        if "type" not in cfg:
            raise KeyError("Config must contain 'type' field")

        obj_type = cfg.pop("type")
        obj_cls = registry.get(obj_type)

        if obj_cls is None:
            raise ValueError(
                f"Module '{obj_type}' not found in registry. Available modules: {list(registry._module_dict.keys())}"
            )

        # Filter parameters based on class __init__ method signature
        init_signature = inspect.signature(obj_cls.__init__)
        valid_params = {}

        for param_name, param in init_signature.parameters.items():
            if param_name == "self":
                continue

            # Handle **kwargs parameters - treat as empty dictionary
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            if param_name in cfg:
                valid_params[param_name] = cfg[param_name]
            elif param.default is not inspect.Parameter.empty:
                # Use default value
                pass
            else:
                # Required parameter but not provided
                raise ValueError(
                    f"Required parameter '{param_name}' not provided for {obj_cls.__name__}"
                )

        return obj_cls(**valid_params)

    def list_modules(self) -> List[str]:
        """
        List all registered module names
        """
        return list(self._module_dict.keys())

    def __contains__(self, name: str) -> bool:
        """
        Check if module is already registered
        """
        return name in self._module_dict

    def __len__(self) -> int:
        """
        Return number of registered modules
        """
        return len(self._module_dict)

    def __repr__(self) -> str:
        return f"Registry(name={self._name}, modules={len(self._module_dict)})"


# Convenience functions
def build_from_cfg(cfg: Dict[str, Any], registry: Registry) -> Any:
    """
    Build object from configuration

    Args:
        cfg: Configuration dictionary
        registry: Registry

    Returns:
        Built object
    """
    return registry.build(cfg)


# Global registries - support automatic loading
BACKENDS = Registry("backend", locations=["backend.vllm.vllm", "backend.openai.openai"])
BENCHMARKS = Registry(
    "benchmark",
    locations=[
        "benchmark.MBPP.MBPP",
        "benchmark.MBPPPlus.MBPPPlus",
        "benchmark.MBPPToy.MBPPToy",
        "benchmark.HumanEval.HumanEval",
        "benchmark.HumanEvalPlus.HumanEvalPlus",
        "benchmark.LeetCode.LeetCode",
        "benchmark.BigCodeBench.BigCodeBench",
        "benchmark.BigCodeBenchHard.BigCodeBenchHard",
    ],
)
EVALUATORS = Registry("evaluator")
MODELS = Registry("model")
DATASETS = Registry("dataset")


# Decorator aliases
def register_backend(name: Optional[str] = None, force: bool = False):
    """Register backend"""
    return BACKENDS.register_module(name, force)


def register_benchmark(name: Optional[str] = None, force: bool = False):
    """Register benchmark"""
    return BENCHMARKS.register_module(name, force)


def register_evaluator(name: Optional[str] = None, force: bool = False):
    """Register evaluator"""
    return EVALUATORS.register_module(name, force)


def register_model(name: Optional[str] = None, force: bool = False):
    """Register model"""
    return MODELS.register_module(name, force)


def register_dataset(name: Optional[str] = None, force: bool = False):
    """Register dataset"""
    return DATASETS.register_module(name, force)
