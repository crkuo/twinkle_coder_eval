# Copyright (c) OpenMMLab. All rights reserved.
import importlib
from typing import Any, Callable, Optional, Tuple, Union


class LazyObject:
    """A wrapper for lazy loading of objects.
    
    LazyObject is used to defer the import and instantiation of objects
    until they are actually needed, which can improve performance and
    avoid circular imports.
    """
    
    def __init__(self, module: str, *args, **kwargs):
        """Initialize LazyObject.
        
        Args:
            module (str): Module path like 'torch.nn.Linear'
            *args: Arguments to pass to the object constructor
            **kwargs: Keyword arguments to pass to the object constructor
        """
        self.module = module
        self.args = args
        self.kwargs = kwargs
        self._built_obj = None
        
    def build(self) -> Any:
        """Build and return the actual object."""
        if self._built_obj is not None:
            return self._built_obj
            
        # Parse module and class name
        parts = self.module.split('.')
        
        # Handle built-in types (no module, just class name)
        if len(parts) == 1:
            class_name = parts[0]
            try:
                # Try to get built-in type from builtins module
                import builtins
                cls = getattr(builtins, class_name)
                self._built_obj = cls(*self.args, **self.kwargs)
                return self._built_obj
            except (AttributeError, TypeError) as e:
                raise ImportError(f"Cannot import built-in type {self.module}: {e}")
        
        # Handle module.class format
        module_name = '.'.join(parts[:-1])
        class_name = parts[-1]
        
        # Import module and get class
        try:
            mod = importlib.import_module(module_name)
            cls = getattr(mod, class_name)
            self._built_obj = cls(*self.args, **self.kwargs)
            return self._built_obj
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {self.module}: {e}")
    
    def __str__(self) -> str:
        return f"LazyObject({self.module})"
    
    def __repr__(self) -> str:
        return f"LazyObject(module='{self.module}', args={self.args}, kwargs={self.kwargs})"


class LazyAttr:
    """A wrapper for lazy loading of attributes/functions.
    
    LazyAttr is used to defer the import of module attributes
    until they are actually needed.
    """
    
    def __init__(self, module: str, attr_name: str = None):
        """Initialize LazyAttr.
        
        Args:
            module (str): Module path like 'torch.nn.functional.relu'
            attr_name (str, optional): Attribute name if not in module path
        """
        if attr_name is None:
            parts = module.split('.')
            self.module = '.'.join(parts[:-1])
            self.attr_name = parts[-1]
        else:
            self.module = module
            self.attr_name = attr_name
        self._built_attr = None
    
    def build(self) -> Any:
        """Build and return the actual attribute."""
        if self._built_attr is not None:
            return self._built_attr
            
        try:
            mod = importlib.import_module(self.module)
            self._built_attr = getattr(mod, self.attr_name)
            return self._built_attr
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {self.module}.{self.attr_name}: {e}")
    
    def __str__(self) -> str:
        return f"{self.module}.{self.attr_name}"
    
    def __repr__(self) -> str:
        return f"LazyAttr(module='{self.module}', attr_name='{self.attr_name}')"