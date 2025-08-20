# Copyright (c) OpenMMLab. All rights reserved.
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

from engine import ConfigDict

# Constants
BASE_KEY = '_base_'
DELETE_KEY = '_delete_'
RESERVED_KEYS = ['filename', 'text', 'pretty_text', 'env_variables']


class Config:
    """A facility for config and config files.

    It supports common file formats as configs: python/json/yaml.
    ``Config.fromfile`` can parse a dictionary from a config file, then
    build a ``Config`` instance with the dictionary.
    The interface is the same as a dict object and also allows access config
    values as attributes.

    Args:
        cfg_dict (dict, optional): A config dictionary. Defaults to None.
        cfg_text (str, optional): Text of config. Defaults to None.
        filename (str or Path, optional): Name of config file.
            Defaults to None.

    Examples:
        >>> cfg = Config(dict(a=1, b=dict(b1=[0, 1])))
        >>> cfg.a
        1
        >>> cfg.b
        {'b1': [0, 1]}
        >>> cfg.b.b1
        [0, 1]
        >>> cfg = Config.fromfile('config.json')
        >>> cfg.filename
        "/path/to/config.json"
    """

    def __init__(
        self,
        cfg_dict: Optional[dict] = None,
        cfg_text: Optional[str] = None,
        filename: Optional[Union[str, Path]] = None,
        env_variables: Optional[dict] = None,
    ):
        """Initialize Config instance."""
        filename = str(filename) if isinstance(filename, Path) else filename
        if cfg_dict is None:
            cfg_dict = dict()
        elif not isinstance(cfg_dict, dict):
            raise TypeError('cfg_dict must be a dict, but '
                            f'got {type(cfg_dict)}')
        
        # Check for reserved keys
        for key in cfg_dict:
            if key in RESERVED_KEYS:
                raise KeyError(f'{key} is reserved for config file')

        if not isinstance(cfg_dict, ConfigDict):
            cfg_dict = ConfigDict(cfg_dict)
        
        super().__setattr__('_cfg_dict', cfg_dict)
        super().__setattr__('_filename', filename)

        if cfg_text:
            text = cfg_text
        elif filename and os.path.exists(filename):
            with open(filename, encoding='utf-8') as f:
                text = f.read()
        else:
            text = ''
        super().__setattr__('_text', text)
        
        if env_variables is None:
            env_variables = dict()
        super().__setattr__('_env_variables', env_variables)

    @staticmethod
    def fromfile(filename: Union[str, Path]) -> 'Config':
        """Build a Config instance from config file.

        Supports JSON, YAML, and simple Python config files.

        Args:
            filename (str or Path): Name of config file.

        Returns:
            Config: Config instance built from config file.
        """
        filename = str(filename) if isinstance(filename, Path) else filename
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Config file '{filename}' not found")
        
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == '.json':
            cfg_dict = Config._load_json(filename)
        elif file_ext in ['.yml', '.yaml']:
            cfg_dict = Config._load_yaml(filename)
        elif file_ext == '.py':
            cfg_dict = Config._load_python(filename)
        else:
            raise ValueError(f"Unsupported config file format: {file_ext}")
        
        return Config(cfg_dict, filename=filename)

    @staticmethod
    def fromstring(cfg_str: str, file_format: str) -> 'Config':
        """Build a Config instance from config text.

        Args:
            cfg_str (str): Config text.
            file_format (str): Config file format (json/yaml/yml).

        Returns:
            Config: Config object generated from ``cfg_str``.
        """
        if file_format not in ['.json', '.yaml', '.yml']:
            raise ValueError(f"Unsupported format: {file_format}")
        
        with tempfile.NamedTemporaryFile(
                'w', encoding='utf-8', suffix=file_format, delete=False) as temp_file:
            temp_file.write(cfg_str)
            temp_file_path = temp_file.name

        try:
            cfg = Config.fromfile(temp_file_path)
            os.remove(temp_file_path)
            return cfg
        except Exception as e:
            os.remove(temp_file_path)
            raise e

    @staticmethod
    def _load_json(filename: str) -> dict:
        """Load JSON config file."""
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _load_yaml(filename: str) -> dict:
        """Load YAML config file."""
        if yaml is None:
            raise ImportError("PyYAML is required to load YAML files. Install it with: pip install PyYAML")
        
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _load_python(filename: str) -> dict:
        """Load simple Python config file."""
        # Simple Python config loader - executes the file and extracts variables
        global_vars = {'__file__': filename}
        local_vars = {}
        
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        try:
            exec(code, global_vars, local_vars)
        except Exception as e:
            raise ValueError(f"Error executing Python config file {filename}: {e}")
        
        # Extract non-private variables
        cfg_dict = {
            key: value for key, value in local_vars.items()
            if not key.startswith('_') and not callable(value)
        }
        
        return cfg_dict

    @property
    def filename(self) -> Optional[str]:
        """Get file name of config."""
        return self._filename

    @property
    def text(self) -> str:
        """Get config text."""
        return self._text

    @property
    def env_variables(self) -> dict:
        """Get used environment variables."""
        return self._env_variables

    def __repr__(self):
        return f'Config (path: {self.filename}): {self._cfg_dict.__repr__()}'

    def __len__(self):
        return len(self._cfg_dict)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cfg_dict, name)

    def __getitem__(self, name):
        return self._cfg_dict.__getitem__(name)

    def __setattr__(self, name, value):
        if isinstance(value, dict):
            value = ConfigDict(value)
        self._cfg_dict.__setattr__(name, value)

    def __setitem__(self, name, value):
        if isinstance(value, dict):
            value = ConfigDict(value)
        self._cfg_dict.__setitem__(name, value)

    def __iter__(self):
        return iter(self._cfg_dict)

    def __deepcopy__(self, memo):
        cls = self.__class__
        other = cls.__new__(cls)
        memo[id(self)] = other

        for key, value in self.__dict__.items():
            super(Config, other).__setattr__(key, copy.deepcopy(value, memo))

        return other

    def __copy__(self):
        cls = self.__class__
        other = cls.__new__(cls)
        other.__dict__.update(self.__dict__)
        super(Config, other).__setattr__('_cfg_dict', self._cfg_dict.copy())

        return other

    copy = __copy__

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key with default."""
        return self._cfg_dict.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        """Pop value by key."""
        return self._cfg_dict.pop(key, default)

    def update(self, other: dict) -> None:
        """Update config with another dictionary."""
        self._cfg_dict.update(other)

    def merge_from_dict(self, options: dict) -> None:
        """Merge list into cfg_dict.

        Merge the dict parsed by dot notation into this cfg.

        Args:
            options (dict): dict of configs to merge from.

        Examples:
            >>> from engine import Config
            >>> options = {'model.backbone.depth': 50, 'model.backbone.with_cp': True}
            >>> cfg = Config(dict(model=dict(backbone=dict(type='ResNet'))))
            >>> cfg.merge_from_dict(options)
            >>> cfg._cfg_dict
            {'model': {'backbone': {'type': 'ResNet', 'depth': 50, 'with_cp': True}}}
        """
        option_cfg_dict = {}
        for full_key, v in options.items():
            d = option_cfg_dict
            key_list = full_key.split('.')
            for subkey in key_list[:-1]:
                d.setdefault(subkey, ConfigDict())
                d = d[subkey]
            subkey = key_list[-1]
            d[subkey] = v

        cfg_dict = super().__getattribute__('_cfg_dict')
        cfg_dict.update(option_cfg_dict)

    def dump(self, file: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Dump config to file or return config text.

        Args:
            file (str or Path, optional): If not specified, then the object
            is dumped to a str, otherwise to a file specified by the filename.
            Defaults to None.

        Returns:
            str or None: Config text.
        """
        file = str(file) if isinstance(file, Path) else file
        cfg_dict = self.to_dict()
        
        if file is None:
            return json.dumps(cfg_dict, indent=2)
        else:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext == '.json':
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(cfg_dict, f, indent=2)
            elif file_ext in ['.yml', '.yaml']:
                if yaml is None:
                    raise ImportError("PyYAML is required to dump YAML files. Install it with: pip install PyYAML")
                with open(file, 'w', encoding='utf-8') as f:
                    yaml.dump(cfg_dict, f, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported dump format: {file_ext}")

    def to_dict(self) -> dict:
        """Convert all data in the config to a builtin ``dict``."""
        return self._cfg_dict.to_dict()

    def merge(self, other: dict) -> None:
        """Merge another dictionary into current config."""
        self._cfg_dict.merge(other)